import psutil
import time
import os

def get_system_metrics():
    """Retrieves real-time system metrics for CPU, Memory, Disk, and Network."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Network I/O
    net_io = psutil.net_io_counters()
    
    return {
        "cpu_usage_percent": cpu_percent,
        "memory": {
            "total": f"{memory.total / (1024**3):.2f} GB",
            "available": f"{memory.available / (1024**3):.2f} GB",
            "percent": memory.percent
        },
        "disk": {
            "total": f"{disk.total / (1024**3):.2f} GB",
            "used": f"{disk.used / (1024**3):.2f} GB",
            "percent": disk.percent
        },
        "network": {
            "bytes_sent": f"{net_io.bytes_sent / (1024**2):.2f} MB",
            "bytes_recv": f"{net_io.bytes_recv / (1024**2):.2f} MB"
        },
        "process_count": len(psutil.pids()),
        "uptime": f"{time.time() - psutil.boot_time():.0f} seconds"
    }

def get_process_info(process_name="python"):
    """Gets performance metrics for processes matching the given name."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu_percent": proc.info['cpu_percent'],
                    "memory_mb": f"{proc.info['memory_info'].rss / (1024**2):.2f} MB"
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes
