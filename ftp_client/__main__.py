import argparse
from ftp_client.cli import CLI

def main():
    parser = argparse.ArgumentParser(description="Secure FTP Client CLI")
    parser.add_argument("--host", required=True, help="FTP server hostname")
    parser.add_argument("--port", type=int, default=21, help="FTP server port")
    parser.add_argument("--user", required=True, help="Username for FTP login")
    parser.add_argument("--pass", dest="password", required=True, help="Password for FTP login")
    args = parser.parse_args()

    cli = CLI(host=args.host, port=args.port, user=args.user, password=args.password)
    try:
        cli.cmdloop()
    finally:
        cli.app.close()

if __name__ == "__main__":
    main()