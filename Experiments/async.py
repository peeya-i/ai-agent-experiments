import asyncio
import time

# 1. Define an asynchronous function (coroutine)
async def fetch_data(task_id, delay):
    print(f"Task {task_id}: Starting...")
    # Simulate a network request using a non-blocking sleep
    await asyncio.sleep(delay) 
    print(f"Task {task_id}: Data received after {delay}s!")
    return f"Result from {task_id}"

# 2. Define the main entry point
async def main():
    # Start both tasks concurrently
    print("Starting all tasks...")
    
    # asyncio.gather fires off multiple tasks at the same time
    results = await asyncio.gather(
        fetch_data("A", 3),
        fetch_data("B", 1)
    )
    print(f"All done! Results: {results}")

# 3. Start the Event Loop and run the main routine
if __name__ == "__main__":
    start_time = time.perf_counter()
    asyncio.run(main())
    print(f"Total time taken: {time.perf_counter() - start_time:.2f} seconds")
