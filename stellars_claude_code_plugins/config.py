from pathlib import Path
import sys

from dotenv import load_dotenv
from loguru import logger

########### SETUP ###############

# set up logger
logger.remove()
logger.add(sys.stdout, colorize=True)

# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    logger.remove()
    logger.add(lambda msg: tqdm.write(msg, end="", file=sys.stdout), colorize=True)
except ModuleNotFoundError:
    pass

########## VARIABLES ############

# Load environment variables from .env file if it exists
load_dotenv()

# paths
PROJ_ROOT = Path(__file__).resolve().parents[1]
REFERENCES_DIR = PROJ_ROOT / "references"

# log current root dir
logger.info(f"PROJ_ROOT path is: {PROJ_ROOT}")
