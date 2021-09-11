import logging
import os
import pickle
import random
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

import hydra
import requests
import requests.auth

LOGFILE = "./get_motivated.log"
logformat = "[%(levelname)s %(asctime)s] %(process)s-%(name)s: %(message)s"
logging.basicConfig(format=logformat, level=logging.INFO, filename=LOGFILE)


def token_generator(cfg):
    token_pkl = Path(cfg.app.token_pkl).expanduser()
    username = cfg.reddit.username
    password = cfg.reddit.password
    client_id = cfg.reddit.client_id
    secret = cfg.reddit.secret

    def token():
        now = datetime.now()

        if token_pkl.exists():
            with open(token_pkl, "rb") as f:
                old_tok = pickle.load(f)
            if old_tok["expiration"] > now:
                return old_tok["access_token"]

        client_auth = requests.auth.HTTPBasicAuth(client_id, secret)
        data = {"grant_type": "password", "username": username, "password": password}
        headers = {"User-Agent": "ChangeMeClient/0.1 by avilay"}
        resp = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=client_auth,
            data=data,
            headers=headers,
        )
        if resp.ok:
            new_tok = resp.json()
            new_tok["expiration"] = now + timedelta(seconds=new_tok["expires_in"])
            with open(token_pkl, "wb") as f:
                pickle.dump(new_tok, f)
            return new_tok["access_token"]
        else:
            logging.error(f"Unable to get auth token. {resp}")
            raise RuntimeError("Unable to get auth token.")

    return token


def open_post(token):
    headers = {
        "Authorization": f"bearer {token()}",
        "User-Agent": "ChangeMeClient/0.1 by avilay",
    }
    resp = requests.get(
        "https://oauth.reddit.com/r/GetMotivated/random", headers=headers
    )
    if resp.ok:
        url = resp.json()[0]["data"]["children"][0]["data"]["url"]
        webbrowser.open(url)
    else:
        logging.error(f"Unable to get content. {resp}")
        raise RuntimeError("Could not get content from Reddit!")


def bootstrap(cfg):
    path = Path(cfg.app.token_pkl).expanduser()
    os.makedirs(path.parent, exist_ok=True)


@hydra.main(config_path=".", config_name="config")
def main(cfg):
    bootstrap(cfg)
    n_errs = 0
    while True:
        try:
            open_post(token_generator(cfg))
            n_errs = 0
            sleep_for_secs = random.randint(2 * 60 * 60, 4 * 60 * 60)
            logging.info(f"Next post in {sleep_for_secs/3600:.2f} hours.")
            time.sleep(sleep_for_secs)
        except KeyboardInterrupt:
            break
        except:  # noqa
            n_errs += 1
            if n_errs >= 3:
                logging.critical("Got three consecutive errors. Stopping.")
                raise RuntimeError("Got three consecutive errors. Stopping.")


if __name__ == "__main__":
    main()
