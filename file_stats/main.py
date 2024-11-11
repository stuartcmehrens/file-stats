import os
import sys
import argparse
from collections import defaultdict, Counter
from pathlib import Path
import heapq
import humanize

def get_file_stats_limited_depth(folder_path, report_depth, top_n_largest_files):
    # Dictionary to store file stats, including the largest files
    file_stats_by_depth = defaultdict(lambda: {
        "count": Counter(),
        "size": Counter(),
        "largest_files": defaultdict(list)  # Track largest files for each extension
    })
    
    # Use an iterative stack-based traversal with scandir for better performance
    stack = [(Path(folder_path), 0)]  # (current_path, current_depth)
    
    while stack:
        current_path, current_depth = stack.pop()
        
        # Skip '.git' directory
        if current_path.name == '.git':
            continue
        
        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    if entry.is_file():
                        # Get file extension and size
                        file_extension = entry.name.split('.')[-1]
                        file_size = entry.stat().st_size
                        
                        # Get limited depth path for reporting purposes
                        report_path = str(current_path.relative_to(folder_path)).split(os.sep)[:report_depth]
                        limited_depth_path = Path(*report_path)
                        
                        # Update counters for the current limited depth path
                        stats = file_stats_by_depth[limited_depth_path]
                        stats["count"][file_extension] += 1
                        stats["size"][file_extension] += file_size
                        
                        # Track largest files using a min-heap to store top N largest files
                        largest_files = stats["largest_files"][file_extension]
                        if len(largest_files) < top_n_largest_files:
                            heapq.heappush(largest_files, (file_size, entry.path))
                        else:
                            heapq.heappushpop(largest_files, (file_size, entry.path))
                        
                    elif entry.is_dir():
                        # Push subdirectory to the stack to process later
                        stack.append((Path(entry.path), current_depth + 1))
        except PermissionError:
            print(f"Skipping {current_path} due to permission error.")
    
    return file_stats_by_depth

def get_overall_stats(file_stats_by_depth):
    """Aggregate overall stats across all folders."""
    overall_stats = {
        "count": Counter(),
        "size": Counter()
    }
    
    for stats in file_stats_by_depth.values():
        overall_stats["count"].update(stats["count"])
        overall_stats["size"].update(stats["size"])
    
    return overall_stats

def format_size(size_in_bytes):
    """Convert size in bytes to a human-readable format (e.g., KB, MB, GB)."""
    return humanize.naturalsize(size_in_bytes)

def print_stats(file_stats, report_depth, top_n_largest_files):
    """Pretty print the file stats."""
    print(f"\n{'='*40}")
    print(f"{'File Type Statistics':^40}")
    print(f"{'='*40}\n")
    
    for folder, stats in file_stats.items():
        print(f"\nFolder (up to depth {report_depth}): {folder}")
        print("-" * (30 + len(str(folder))))
        print(f"{'File Type':<20}{'Count':<10}{'Total Size':<20}")
        print("-" * 50)
        
        for file_type, count in stats["count"].items():
            total_size = stats["size"][file_type]
            print(f"{file_type:<20}{count:<10}{format_size(total_size):<20}")

            # Print the largest files for each type
            largest_files = sorted(stats["largest_files"][file_type], reverse=True)
            print(f"    Largest {min(len(largest_files), top_n_largest_files)} files:")
            for file_size, file_path in largest_files:
                print(f"      {file_path} - {format_size(file_size)}")

def print_overall_stats(overall_stats):
    """Pretty print the overall file stats, sorted by count and then by total size."""
    print(f"\n{'='*40}")
    print(f"{'Overall File Type Summary':^40}")
    print(f"{'='*40}\n")
    print(f"{'File Type':<20}{'Count':<10}{'Total Size':<20}")
    print("-" * 50)
    
    # Sort by count first, then by total size if counts are the same
    sorted_stats = sorted(
        overall_stats["count"].items(),
        key=lambda item: (-item[1], -overall_stats["size"][item[0]])
    )
    
    for file_type, count in sorted_stats:
        total_size = overall_stats["size"][file_type]
        print(f"{file_type:<20}{count:<10}{format_size(total_size):<20}")

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Analyze file types and sizes in a folder.")
    
    parser.add_argument("folder_path", type=str, help="The path of the folder to analyze.")
    parser.add_argument("--depth", type=int, default=2, help="Depth to limit the folder path in the report (default is 2).")
    parser.add_argument("--top-n", type=int, default=5, help="Number of largest files to display per file type (default is 3).")
    
    args = parser.parse_args()
    
    folder_path = args.folder_path
    report_depth = args.depth
    top_n_largest_files = args.top_n
    
    if not os.path.isdir(folder_path):
        print(f"The specified path '{folder_path}' is not a directory.")
        sys.exit(1)

    # Call the file stats function
    file_stats = get_file_stats_limited_depth(folder_path, report_depth, top_n_largest_files)

    # Calculate and print the overall stats
    overall_stats = get_overall_stats(file_stats)
    print_overall_stats(overall_stats)
    
    # Display the per-folder results
    print_stats(file_stats, report_depth, top_n_largest_files)

if __name__ == "__main__":
    main()
