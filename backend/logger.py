import logging
from logging import FileHandler,StreamHandler
import os 

os.makedirs("log",exist_ok=False)
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
     handlers=[
         FileHandler("log/log.txt"),
         StreamHandler()
     ] )

logger=logging.getLogger(__name__)


logger.info("sucessfully imported logger module")
