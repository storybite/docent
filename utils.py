import os
from openai import OpenAI
from dataclasses import dataclass, field
import pytz
from datetime import datetime, timedelta
import json
import warnings
import pickle
import pandas as pd
import mysql.connector
from enum import Enum
import tiktoken
from importlib import reload
from typing import List
import uuid
import base64
import shutil

warnings.filterwarnings("ignore", category=UserWarning, module="onnxruntime")


def rl(module):
    reload(module)


def generate_unique_value():
    unique_id = uuid.uuid4()
    unique_str = base64.urlsafe_b64encode(unique_id.bytes).rstrip(b"=").decode("utf-8")
    return unique_str


@dataclass(frozen=True)
class Model:
    basic: str = "gpt-3.5-turbo-1106"
    # advanced: str = "gpt-4-1106-preview"
    advanced: str = "gpt-4o"


model = Model()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30, max_retries=1)

server_started_time = ""


def nvl(x, y) -> str:
    if x == None:
        return y
    else:
        return x


def generate_unique_value():
    unique_id = uuid.uuid4()
    unique_str = base64.urlsafe_b64encode(unique_id.bytes).rstrip(b"=").decode("utf-8")
    return unique_str


def makeup_response(message, finish_reason="ERROR"):
    return {
        "id": f"makeup-{generate_unique_value()}",
        "choices": [
            {
                "finish_reason": finish_reason,
                "index": 0,
                "message": {"role": "assistant", "content": message},
            }
        ],
        "usage": {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0},
    }


def today(fmt=""):
    korea = pytz.timezone("Asia/Seoul")  # 한국 시간대를 얻습니다.
    now = datetime.now(korea)  # 현재 시각을 얻습니다.
    now = now.strftime("%Y%m%d")  # 시각을 원하는 형식의 문자열로 변환합니다.
    year = now[:4]
    month = now[4:6]
    day = now[6:]
    return f"{year}{fmt}{month}{fmt}{day}"


def yesterday():
    korea = pytz.timezone("Asia/Seoul")  # 한국 시간대를 얻습니다.
    now = datetime.now(korea)  # 현재 시각을 얻습니다.
    one_day = timedelta(days=1)  # 하루 (1일)를 나타내는 timedelta 객체를 생성합니다.
    yesterday = now - one_day  # 현재 날짜에서 하루를 빼서 어제의 날짜를 구합니다.
    return yesterday.strftime("%Y%m%d")  # 어제의 날짜를 yyyymmdd 형식으로 변환합니다.


def curr_time(fmt=""):
    # 한국 시간대를 얻습니다.
    korea = pytz.timezone("Asia/Seoul")
    # 현재 시각을 얻습니다.
    now = datetime.now(korea)
    # 시각을 원하는 형식의 문자열로 변환합니다.
    formatted_now = now.strftime(f"%Y{fmt}%m{fmt}%d %H:%M:%S")
    return formatted_now


def read_file(file_path, encoder="utf-8"):
    with open(file_path, "r", encoding=encoder) as file:
        content = file.read()
    return content


def write_file(file_path, content, encoder="utf-8"):
    with open(file_path, "w", encoding=encoder) as file:
        file.write(content)


def delete_dir(dir_path):

    # 폴더가 존재하는지 확인
    if os.path.exists(dir_path):
        # 폴더 내의 모든 파일 삭제
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"오류 발생: {e}")
        print(f"{dir_path}폴더 내 모든 파일이 삭제되었습니다.")
    else:
        print(f"{dir_path} 폴더가 존재하지 않습니다.")


def json_request(message, model=model.advanced):
    # print(f"json_request message strt:\n{message}\njson_request message end")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            temperature=0,
            top_p=0,
            response_format={"type": "json_object"},
            seed=1234,
        ).model_dump()
    except Exception as e:
        print(f"Exception 오류({type(e)}) 발생:{e}")
        raise e

    json_result = json.loads(response["choices"][0]["message"]["content"])
    return response, json_result


def request(message, model=model.advanced):
    # print(f"request message strt:\n{message}\nrequest message end")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": message}],
            temperature=0,
            top_p=0,
            seed=1234,
        ).model_dump()
    except Exception as e:
        print(f"Exception 오류({type(e)}) 발생:{e}")
        raise e

    return response, response["choices"][0]["message"]["content"]


def sys_json_request(system_prompt, message, model=model.advanced):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0,
            top_p=0,
            response_format={"type": "json_object"},
            seed=1234,
        ).model_dump()
    except Exception as e:
        print(f"Exception 오류({type(e)}) 발생:{e}")
        raise e

    json_result = json.loads(response["choices"][0]["message"]["content"])
    return response, json_result


class Dct:

    @staticmethod
    def idx_to_key(dct: dict, idx: int) -> str:
        return list(dct.keys())[idx]

    @staticmethod
    def idx_to_val(dct: dict, idx: int = 0) -> str:
        return list(dct.values())[idx]

    @staticmethod
    def key_to_idx(dct: dict, key: str) -> str:
        keys = list(dct.keys())
        return keys.index(key)


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def extract_c_functions(source_code):
    pattern = r"""
        (\w+\s+\*?\s*\w+\s*)\(
        [^)]*\)
        \s*{(?:[^{}]|{(?:[^{}]|{[^{}]*})*})*}
    """
    func_pattern = re.compile(pattern, re.VERBOSE | re.MULTILINE)
    functions = func_pattern.finditer(source_code)
    return [match.group(0) for match in functions]


def remove_technical_comments(source_code, keyword):
    lines = source_code.split("\n")
    filtered_lines = [
        line
        for line in lines
        if keyword not in line or not line.strip().startswith("/*")
    ]
    return "\n".join(filtered_lines)


def extract_non_function_code(source_code):
    func_pattern = r"""
        (\w+\s+\*?\s*\w+\s*)\(
        [^)]*\)
        \s*{(?:[^{}]|{(?:[^{}]|{[^{}]*})*})*}
    """

    def remove_functions(code):
        code = re.sub(func_pattern, "", code, flags=re.VERBOSE)
        code = re.sub(r"\n\s*\n\s*\n\s*\n", "\n\n", code)
        return code.strip()

    non_function_code = remove_functions(source_code)
    result = []
    for line in non_function_code.split("\n"):
        if line.strip():
            result.append(line.rstrip())
        else:
            result.append("")

    return "\n".join(result)


def extract_c_function_name(line):
    line = line.strip()
    paren_index = line.find("(")
    if paren_index == -1:
        return None
    prefix = line[:paren_index]
    last_space = prefix.rfind(" ")
    if last_space == -1:
        return None
    return prefix[last_space + 1 :]


def connect_db(close=False):
    connection = None

    def connect_db0():
        nonlocal connection
        if connection:
            return connection
        with open("D:/workspace/sts/poc/bot/db_config.pkl", "rb") as config_file:
            db_config = pickle.load(config_file)
        try:
            connection = mysql.connector.connect(**db_config)
            return connection
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None

    if close:
        if connection:
            connection.close()
        else:
            return None
    else:
        return connect_db0()


class Timer:

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = datetime.now()

    def stop(self):
        self.end_time = datetime.now()

    def elapsed_time(self):
        if self.start_time and self.end_time:
            elapsed = self.end_time - self.start_time
            return elapsed.total_seconds()
        else:
            return 999_999_999

    def get_start_time(self):
        return int(self.start_time.strftime("%Y%m%d%H%M%S"))

    def get_end_time(self):
        return int(self.end_time.strftime("%Y%m%d%H%M%S"))


def write_pickle(data, filename):
    with open(filename, "wb") as f:  # 'wb'는 write binary 모드를 의미
        pickle.dump(data, f)


def read_pickle(filename):
    with open(filename, "rb") as f:  # 'rb'는 read binary 모드를 의미
        data = pickle.load(f)
    return data
