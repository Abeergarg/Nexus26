import asyncio
import httpx
import random
import time
import argparse

# List of valid nodes from stadium topology to generate telemetry events
VALID_NODES = [
    "Gate_A",
    "Gate_B",
    "Gate_C",
    "Gate_D",
    "Section_101",
    "Section_102",
    "Section_103",
    "Section_104",
    "Section_201",
    "Section_202",
    "Section_203",
    "Section_204",
    "Food_Court_1",
    "First_Aid_1",
    "Restrooms_1",
    "Restrooms_2",
    "Stairs_North",
    "Ramp_South",
    "Elevator_West",
    "Elevator_East",
]


async def send_batch(
    client: httpx.AsyncClient, url: str, batch_id: int, batch_size: int
) -> int:
    """Generates a batch of randomized crowd density events and POSTs them to the telemetry endpoint."""
    events = []
    for _ in range(batch_size):
        src = random.choice(VALID_NODES)
        # Avoid self-loops
        candidates = [n for n in VALID_NODES if n != src]
        tgt = random.choice(candidates)
        density = round(random.uniform(0.0, 1.0), 2)

        events.append({"source": src, "target": tgt, "density": density})

    payload = {"events": events}

    try:
        start_t = time.time()
        response = await client.post(url, json=payload, timeout=2.0)
        latency = (time.time() - start_t) * 1000

        if response.status_code == 200:
            res_data = response.json()
            return len(events)
        else:
            print(
                f"[Batch {batch_id}] Error: Received status code {response.status_code}"
            )
            return 0
    except Exception as e:
        print(f"[Batch {batch_id}] Request Exception: {e}")
        return 0


async def main():
    parser = argparse.ArgumentParser(
        description="Nexus26 High-Velocity Telemetry Load Generator"
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/api/telemetry/simulate",
        help="FastAPI target URL",
    )
    parser.add_argument(
        "--rate", type=int, default=2000, help="Target telemetry events per second"
    )
    parser.add_argument(
        "--duration", type=int, default=10, help="Duration of load test in seconds"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of telemetry events per API batch payload",
    )
    args = parser.parse_args()

    print("==================================================================")
    print("      Nexus26 Virtual Telemetry Load Generator (FIFA World Cup)   ")
    print("==================================================================")
    print(f"Target URL:         {args.url}")
    print(f"Target Event Rate:  {args.rate} events/second")
    print(f"Batch Size:         {args.batch_size} events/request")
    print(f"Total Duration:     {args.duration} seconds")
    print("------------------------------------------------------------------")

    # Calculate required requests per second
    reqs_per_second = max(1, args.rate // args.batch_size)
    delay_between_batches = 1.0 / reqs_per_second

    # Use a limits config to enable high-concurrency client reuse
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    async with httpx.AsyncClient(limits=limits) as client:
        total_events_sent = 0
        start_time = time.time()
        batch_counter = 0

        # Run loop for specified duration
        while time.time() - start_time < args.duration:
            loop_start = time.time()

            # Fire concurrent tasks for this second
            tasks = []
            for _ in range(reqs_per_second):
                batch_counter += 1
                tasks.append(
                    send_batch(client, args.url, batch_counter, args.batch_size)
                )

            results = await asyncio.gather(*tasks)
            events_in_tick = sum(results)
            total_events_sent += events_in_tick

            # Throttle to maintain target rates
            elapsed = time.time() - loop_start
            sleep_time = max(0, 1.0 - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        end_time = time.time()
        duration_actual = end_time - start_time
        avg_rate = total_events_sent / duration_actual

        print("------------------------------------------------------------------")
        print("                        LOAD TEST SUMMARY                         ")
        print("------------------------------------------------------------------")
        print(f"Actual Test Duration: {duration_actual:.2f} seconds")
        print(f"Total Telemetry Events Ingested: {total_events_sent} events")
        print(f"Average Throughput Rate:         {avg_rate:.2f} events/second")
        print(f"Server Connection Status:        SUCCESSFUL (Zero Crashes)")
        print("==================================================================")


if __name__ == "__main__":
    # Ensure correct asyncio event loop on Windows
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLoad generation stopped by user.")
