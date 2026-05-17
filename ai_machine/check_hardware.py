import torch
import psutil
import platform
import sys

def check_hardware():
    print("--------------------------------------------------")
    print("   FERWAFA AI Pitch Machine - Hardware Diagnostic")
    print("--------------------------------------------------")
    
    status = {
        "os": platform.system(),
        "processor": platform.processor(),
        "cuda": False,
        "mps": False,
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "cores": psutil.cpu_count(logical=True),
        "elite_ready": False
    }

    print(f"[*] OS Detected: {status['os']} ({platform.release()})")
    print(f"[*] CPU Cores: {status['cores']}")
    print(f"[*] System RAM: {status['ram_gb']} GB")

    # 🟢 NVIDIA CUDA Check
    if torch.cuda.is_available():
        status["cuda"] = True
        status["elite_ready"] = True
        gpu_name = torch.cuda.get_device_name(0)
        print(f"[+] NVIDIA GPU Detected: {gpu_name} (CUDA ENABLED)")
    else:
        print("[ ] No NVIDIA GPU detected.")

    # 🟢 Apple Silicon MPS Check
    if status["os"] == "Darwin":
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            status["mps"] = True
            status["elite_ready"] = True
            print("[+] Apple Silicon (MPS) Detected: High Speed Inference Enabled")
        else:
            print("[ ] No Apple Silicon acceleration found.")

    # 🟡 Performance Baseline Check
    if not status["elite_ready"]:
        if status["ram_gb"] >= 16 and status["cores"] >= 8:
            status["elite_ready"] = True
            print("[!] Warning: Running on High-End CPU only. Real-time performance may vary.")
        else:
            print("[!] CRITICAL: Low-performance hardware detected. YOLO tracking might be slow.")

    print("--------------------------------------------------")
    if status["elite_ready"]:
        print(">>> SUCCESS: This machine is ELITE READY.")
    else:
        print(">>> WARNING: Hardware might not support real-time tracking.")
    print("--------------------------------------------------")
    
    return status

if __name__ == "__main__":
    check_hardware()
