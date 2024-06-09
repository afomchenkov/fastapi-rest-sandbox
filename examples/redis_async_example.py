import asyncio
import redis.asyncio as redis


async def main():
    # Create a connection to the Redis server
    client = redis.Redis(host="localhost", port=6379, db=0)

    # Execute a command asynchronously
    result = await client.execute_command("SET", "my_key", "my_value")
    print(f"SET command result: {result}")

    # Execute another command to retrieve the value
    value = await client.execute_command("GET", "my_key")
    print(f"GET command result: {value}")

    # Closing the client connection
    await client.close()


# Run the main function
asyncio.run(main())
