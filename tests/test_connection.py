import sys
import MetaTrader5 as mt5

# Explicit path to your portable / USB HFM MT5 executable
TERMINAL_PATH = r"E:\Programs\Program Files (USB)\HFM Metatrader 5\terminal64.exe"
ACCOUNT_ID = 57505711
PASSWORD = "Nvd733,Ma"
SERVER = "HFMarketsKE-Demo2"

def run_handshake():
    print("=== ATHENA MT5 Terminal Diagnostic Handshake ===")

    # 2. Terminal Launch & Initialization
    print(f"\n[1/3] Launching terminal process at:\n      {TERMINAL_PATH}")
    if not mt5.initialize(path=TERMINAL_PATH):
        error_code = mt5.last_error()
        print(f"[FAILED] Terminal launch or IPC init failed: {error_code}")
        sys.exit(1)

    print("[SUCCESS] MT5 Terminal launched and connected via IPC.")

    # 3. Account Authentication Handshake
    print(f"\n[2/3] Authenticating Account {ACCOUNT_ID} on server '{SERVER}'...")
    authorized = mt5.login(login=ACCOUNT_ID, password=PASSWORD, server=SERVER)

    if not authorized:
        error_code = mt5.last_error()
        print(f"[FAILED] Authentication failed: {error_code}")
        mt5.shutdown()
        sys.exit(1)

    print("[SUCCESS] Broker Handshake Authorized!")

    # 4. Telemetry Telemetry Verification
    print("\n[3/3] Pulling account telemetry...")
    account_info = mt5.account_info()

    if account_info is not None:
        print("\n==============================================")
        print(f" Account Number : {account_info.login}")
        print(f" Broker / Host  : {account_info.company}")
        print(f" Connected Server: {account_info.server}")
        print(f" Account Balance: {account_info.balance:.2f} {account_info.currency}")
        print(f" Leverage Ratio : 1:{account_info.leverage}")
        print(f" Algo Trading   : {'ALLOWED' if account_info.trade_allowed else 'DISABLED'}")
        print("==============================================")
    else:
        print("[WARNING] Authenticated, but failed to fetch account_info().")

    mt5.shutdown()
    print("\n[COMPLETE] Handshake test completed. Terminal process disconnected successfully.")

if __name__ == "__main__":
    run_handshake()