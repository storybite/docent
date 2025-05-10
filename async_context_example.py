import asyncio
from contextlib import AsyncExitStack
import random


class DatabaseConnection:
    def __init__(self, name):
        self.name = name
        self.connected = False

    async def __aenter__(self):
        # DB 연결 시뮬레이션
        await asyncio.sleep(0.5)  # 연결 시간 시뮬레이션
        self.connected = True
        print(f"DB {self.name}에 연결되었습니다.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connected:
            await asyncio.sleep(0.2)  # 연결 해제 시간 시뮬레이션
            print(f"DB {self.name} 연결이 해제되었습니다.")

    async def query(self, query_text):
        if not self.connected:
            raise Exception("DB에 연결되어 있지 않습니다.")
        await asyncio.sleep(0.1)  # 쿼리 실행 시간 시뮬레이션
        return f"{self.name}에서 '{query_text}' 쿼리 실행 결과"


async def main():
    print("\n1. 일반적인 async with 사용 (단순한 경우)")
    try:
        async with DatabaseConnection("main_db") as db:
            result = await db.query("SELECT * FROM users")
            print(result)
    except Exception as e:
        print(f"에러 발생: {e}")

    print("\n2. AsyncExitStack 사용 (복잡한 경우)")
    try:
        async with AsyncExitStack() as exit_stack:
            # 필요한 DB 연결들을 동적으로 생성
            dbs = []
            for i in range(3):
                db = await exit_stack.enter_async_context(DatabaseConnection(f"db_{i}"))
                dbs.append(db)

            # 모든 DB에 쿼리 실행
            for db in dbs:
                result = await db.query("SELECT * FROM users")
                print(result)

            # 특정 조건에 따라 추가 DB 연결
            if random.random() > 0.5:
                extra_db = await exit_stack.enter_async_context(
                    DatabaseConnection("extra_db")
                )
                result = await extra_db.query("SELECT * FROM logs")
                print(result)

    except Exception as e:
        print(f"에러 발생: {e}")

    print("\n3. AsyncExitStack의 장점: 동적 리소스 관리")
    try:
        async with AsyncExitStack() as exit_stack:
            # 첫 번째 DB 연결
            db1 = await exit_stack.enter_async_context(DatabaseConnection("primary"))
            result1 = await db1.query("SELECT * FROM users")
            print(result1)

            # 조건에 따라 두 번째 DB 연결
            if random.random() > 0.5:
                db2 = await exit_stack.enter_async_context(
                    DatabaseConnection("secondary")
                )
                result2 = await db2.query("SELECT * FROM logs")
                print(result2)

            # 에러 발생 시뮬레이션
            if random.random() > 0.7:
                raise Exception("예상치 못한 에러 발생!")

    except Exception as e:
        print(f"에러 발생: {e}")
        # AsyncExitStack이 자동으로 모든 리소스를 정리합니다


if __name__ == "__main__":
    asyncio.run(main())
