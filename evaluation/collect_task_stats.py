# Implements basic collection of task statistics

import json
import time
import typer

from ray.util.state import list_tasks

app = typer.Typer()

@app.command()
def collect_stats(
    interval: int = typer.Option(300, help="Interval in ms to collect stats"),
    outfile: str = typer.Option("task_stats.json", help="Output file to write stats to"),
):
    fd = open(outfile, "w")

    while True:
        finished = list_tasks(filters=[("state", "=", "FINISHED")], detail=True, limit=1000)

        stats = {}

        for task in finished:
            task_id = task.task_id
            create_time_ms = task.creation_time_ms
            start_time_ms = task.start_time_ms
            end_time_ms = task.end_time_ms
            stats[task_id] = {"creation_time_ms": create_time_ms, "start_time_ms": start_time_ms, "end_time_ms": end_time_ms}

        fd.write(json.dumps(stats) + "\n")

        print(f"{stats}")
        time.sleep(interval/1000.0)


@app.command()
def analyze_stats(
    infile: str = typer.Option("task_stats.json", help="Input file to read stats from"),
    interval: int = typer.Option(300, help="Interval in ms to collect stats"),
    outfile: str = typer.Option("task_stats_analysis.json", help="Output file to write stats to"),
):
    with open(infile, "r") as fd:
        data = fd.read()

    last_line = data.split("\n")[-2]
    # print(last_line)
    data = json.loads(last_line)
    # print(data)

    running_times = []
    waiting_times = []

    all_create_times = []
    all_start_times = []
    all_end_times = []

    for task, details in data.items():
        create_time_ms = details["creation_time_ms"]
        start_time_ms = details["start_time_ms"]
        end_time_ms = details["end_time_ms"]

        running_times.append(end_time_ms - start_time_ms)
        waiting_times.append(start_time_ms - create_time_ms)

        all_create_times.append(create_time_ms)
        all_start_times.append(start_time_ms)
        all_end_times.append(end_time_ms)

    all_create_times.sort()
    all_start_times.sort()
    all_end_times.sort()
    
    print(len(all_create_times), len(all_start_times), len(all_end_times))
    idx = all_create_times[0]

    waiting_count = {}
    running_count = {}
    completed_count = {}

    w_idx = 0
    r_idx = 0
    c_idx = 0

    while idx < all_end_times[-1] + interval:
        while w_idx < len(all_create_times) and all_create_times[w_idx] <= idx:
            w_idx += 1

        while r_idx < len(all_start_times) and all_start_times[r_idx] <= idx:
            r_idx += 1

        while c_idx < len(all_end_times) and all_end_times[c_idx] <= idx:
            c_idx += 1

        waiting_count[idx] = w_idx - r_idx
        running_count[idx] = r_idx - c_idx
        completed_count[idx] = c_idx

        idx += interval

    stats = {
        "running_times": running_times,
        "waiting_times": waiting_times,
        "waiting_count": waiting_count,
        "running_count": running_count,
        "completed_count": completed_count,
    }

    with open(outfile, "w") as fd:
        fd.write(json.dumps(stats))


if __name__ == "__main__":
    app()