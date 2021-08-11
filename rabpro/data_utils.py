"""
Data utility functions (data_utils.py)
======================================

"""

import json
import os
import re
import shutil
import tarfile
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import appdirs
import requests
import tqdm
from bs4 import BeautifulSoup

_DATAPATH = Path(appdirs.user_data_dir("rabpro", "rabpro"))

_PATH_CONSTANTS = {
    "HydroBasins1": f"HydroBasins{os.sep}level_one",
    "HydroBasins12": f"HydroBasins{os.sep}level_twelve",
    "DEM_fdr": f"DEM{os.sep}MERIT_FDR{os.sep}MERIT_FDR.vrt",
    "DEM_uda": f"DEM{os.sep}MERIT_UDA{os.sep}MERIT_UDA.vrt",
    "DEM_elev_hp": f"DEM{os.sep}MERIT_ELEV_HP{os.sep}MERIT_ELEV_HP.vrt",
    "DEM_width": f"DEM{os.sep}MERIT_WTH{os.sep}MERIT_WTH.vrt",
}

CATALOG_URL = "https://raw.githubusercontent.com/jonschwenk/rabpro/main/Data/gee_datasets.json"

_GEE_CACHE_DAYS = 1

merit_hydro_paths = {
    "elv": f"DEM{os.sep}MERIT_ELEV_HP",
    "dir": f"DEM{os.sep}MERIT_FDR",
    "upa": f"DEM{os.sep}MERIT_UDA",
    "wth": f"DEM{os.sep}MERIT_WTH",
}


def create_datapaths(datapath=None, configpath=None):
    global _DATAPATH
    if datapath is None:
        try:
            datapath = Path(os.environ["RABPRO_DATA"])
        except:
            datapath = Path(appdirs.user_data_dir("rabpro", "rabpro"))

    _DATAPATH = datapath

    if configpath is None:
        try:
            configpath = Path(os.environ["RABPRO_CONFIG"])
        except:
            configpath = Path(appdirs.user_config_dir("rabpro", "rabpro"))

    datapaths = {key: str(datapath / Path(val)) for key, val in _PATH_CONSTANTS.items()}
    gee_metadata_path = datapath / "gee_datasets.json"
    datapaths["gee_metadata"] = str(gee_metadata_path)

    # User defined GEE datasets
    user_gee_metadata_path = configpath / "user_gee_datasets.json"
    datapaths["user_gee_metadata"] = str(user_gee_metadata_path)
    if not user_gee_metadata_path.is_file():
        datapaths["user_gee_metadata"] = None

    return datapaths


def download_gee_metadata():
    gee_metadata_path = _DATAPATH / "gee_datasets.json"

    # Download catalog JSON file
    if gee_metadata_path.is_file():
        mtime = datetime.fromtimestamp(gee_metadata_path.stat().st_mtime)
        delta = datetime.now() - mtime

    if not gee_metadata_path.is_file() or delta > timedelta(days=_GEE_CACHE_DAYS):
        try:
            response = requests.get(CATALOG_URL)
            if response.status_code == 200:
                r = response.json()
                with open(gee_metadata_path, "w") as f:
                    json.dump(r, f, indent=4)
            else:
                print(
                    f"{CATALOG_URL} returned error status code {response.status_code}. Download manually into {gee_metadata_path}"
                )
        except Exception as e:
            print(e)


def merit_hydro(target, username, password, proxy=None, clean=True):
    baseurl = "http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_Hydro/"

    if proxy is not None:
        response = requests.get(baseurl, proxies={"http": proxy})
    else:
        response = requests.get(baseurl)
    soup = BeautifulSoup(response.text, "html.parser")
    urls = [x["href"][2:] for x in soup.findAll("a", text=re.compile(target), href=True)]
    # The [2:] gets rid of the "./" in the URL

    if len(urls) == 0:
        raise ValueError(f"No tile matching '{target}' found.")

    for urlfile in urls:
        url = baseurl + urlfile
        filename = os.path.basename(urllib.parse.urlparse(url).path)

        if filename[:3] not in merit_hydro_paths:
            continue

        filename = os.path.join(_DATAPATH, merit_hydro_paths[filename[:3]], filename)
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        download_tar_file(url, filename, username, password, proxy, clean)


def download_tar_file(url, filename, username, password, proxy=None, clean=True):
    if not clean:
        if os.path.isfile(filename):
            return

    print(f"Downloading '{url}' into '{filename}'")

    if proxy is not None:
        r = requests.get(url, auth=(username, password), stream=True, proxies={"http": proxy})
    else:
        r = requests.get(url, auth=(username, password), stream=True)

    total_size = int(r.headers.get("content-length", 0))

    if r.status_code != 200:
        print(f"{url} failed with status code {r.status_code}")
        return

    with open(filename, "wb") as f:
        tqdmbar = tqdm.tqdm(total=total_size, unit="B", unit_scale=True)
        for chunk in r.iter_content(4 * 1024):
            if chunk:
                tqdmbar.update(len(chunk))
                f.write(chunk)
        tqdmbar.close()

    # Extract TAR archive and remove artifacts
    with tarfile.open(filename) as tf:
        tf.extractall(os.path.dirname(filename))

    tar_dir = filename[:-4]
    files = os.listdir(tar_dir)
    for f in files:
        shutil.move(os.path.join(tar_dir, f), os.path.join(os.path.dirname(tar_dir), f))

    if not clean:
        os.rmdir(tar_dir)
        os.remove(filename)


_HYDROBASINS_IDS = {
    "dbf": "1duRlrrHTciKn7gM4qogumZ4OhqrB0Ggq",
    "prj": "1fSAUKiFbfYb8-rLqiG1Epo3dMNLBOMHh",
    "qpj": "1ZMCrzYUJuxORxNwkQjL1qvFHODS64WBu",
    "shp": "1ev5Md5d2RwzpTRfpJ6SmCkYPf_7821b2",
    "shx": "15-fa27DPnioY9kDzgKHQdaSxingSGhCJ",
}


def hydrobasins(proxy=None, clean=True):
    filebase = "hybas_all_lev01_v1c."
    urlbase = "https://drive.google.com/uc?export=download&id="
    pathbase = _DATAPATH / Path(_PATH_CONSTANTS["HydroBasins1"])

    os.makedirs(pathbase, exist_ok=True)

    for ext in _HYDROBASINS_IDS:
        filename = pathbase / Path(filebase + ext)
        url = urlbase + _HYDROBASINS_IDS[ext]

        if not clean:
            if os.path.isfile(filename):
                return

        print(f"Downloading '{url}' into '{filename}'")

        if proxy is not None:
            r = requests.get(url, stream=True, proxies={"http": proxy})
        else:
            r = requests.get(url, stream=True)

        total_size = int(r.headers.get("content-length", 0))

        if r.status_code != 200:
            print(f"{url} failed with status code {r.status_code}")
            return

        with open(filename, "wb") as f:
            tqdmbar = tqdm.tqdm(total=total_size, unit="B", unit_scale=True)
            for chunk in r.iter_content(4 * 1024):
                if chunk:
                    tqdmbar.update(len(chunk))
                    f.write(chunk)
            tqdmbar.close()
