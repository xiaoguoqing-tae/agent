from core.config import conf
from utils.file import get_abs_path
from datetime import datetime
import logging
import os

os.makedirs(get_abs_path(conf["log"]["dir"]),exist_ok=True)

def get_logger(
        name:str,
        console_level:int,
        file_level:int,
        log_file:None
)->logging.Logger:
    """
    获取日志句柄
    :param name:
    :param console_level:
    :param file_level:
    :param log_file:
    :return:
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    #避免重复添加 handler
    if logger.handlers:
        return logger

    #控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(conf["log"]["formatter"]))
    logger.addHandler(console_handler)

    if not log_file:
        log_file = os.path.join(get_abs_path(conf["log"]["dir"]),f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file,encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(conf["log"]["formatter"]))
    logger.addHandler(file_handler)
    return logger

logger = get_logger("app",logging.INFO,logging.DEBUG,None)

if __name__ == "__main__":
    logger.info("张无忌的信息")
    logger.warning("张无忌的警告")
    logger.error("张无忌严重受伤")
    logger.debug("张无忌正在修炼九阳神功")