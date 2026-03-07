import asyncio

from src.clients.api_football import APIFootballClient


async def main():
    client = APIFootballClient()
    try:
        fixture = await client.get_fixture(1523413)  # Newcastle vs Man City
        if "lineups" in fixture:
            for t in fixture["lineups"]:
                if t["team"]["id"] == 34:
                    print("Newcastle Lineup:")
                    for p in t["startXI"]:
                        print(f"{p['player']['id']}: {p['player']['name']}")
        else:
            print("No lineups found for fixture " + str(1523413))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
