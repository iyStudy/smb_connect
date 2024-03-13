from smb.SMBConnection import SMBConnection
import subprocess
import os
import datetime
import tkinter as tk
import importlib.util
from datetime import datetime

# 設定ファイルパス
config_path = 'config.py'

# config.py が存在しない場合は作成する
if not os.path.exists(config_path):
    server_ip = ''  # サーバーのIPアドレス
    username = ''  # ユーザー名
    password = ''  # パスワード
    client_machine = subprocess.check_output('hostname').strip().decode()
    server_domain = ''  # ドメインが不要な場合は空白
    local_directory_path = ''
    shared_resource = ''  # 共有リソース名
    remote_directory_path = ''  # ルートディレクトリ、または同期したい特定のパス

    with open(config_path, 'w') as f:
        f.write(f"""
# config.py
SERVER_IP = '{server_ip}'
USERNAME = '{username}'
PASSWORD = '{password}'
CLIENT_MACHINE = '{subprocess.check_output('hostname').strip().decode()}'
SERVER_DOMAIN = ''
LOCAL_DIRECTORY_PATH = r'{local_directory_path}'
SHARED_RESOURCE = '{shared_resource}'
REMOTE_DIRECTORY_PATH = '{remote_directory_path}'
""")
    print(f"{config_path} has been created with default settings.")

# config.py の設定を読み込む
spec = importlib.util.spec_from_file_location("config", config_path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)



server_ip = config.SERVER_IP  # サーバーのIPアドレス
username = config.USERNAME  # ユーザー名
password = config.PASSWORD  # パスワード
client_machine = subprocess.check_output('hostname').strip().decode()
server_domain = ''  # ドメインが不要な場合は空白
local_directory_path = config.LOCAL_DIRECTORY_PATH
shared_resource = config.SHARED_RESOURCE
remote_directory_path = config.REMOTE_DIRECTORY_PATH


def list_remote_directory_contents(conn, share_name, directory_path):
    """
    リモートディレクトリ内の内容をリストアップします。
    """
    print(f"Listing contents of {directory_path} on {share_name}:")
    try:
        files = conn.listPath(share_name, directory_path)
        for f in files:
            if f.filename not in ['.', '..']:
                print(f.filename)
    except Exception as e:
        print(f"Error accessing {directory_path} on {share_name}: {e}")
        lb_msg.config(text=f"Error accessing {directory_path} on {share_name}: {e}")


def update_remote_file(conn, local_path, remote_path, share_name):
    """
    ローカルファイルをリモートに更新。
    """
    with open(local_path, 'rb') as file_obj:
        conn.storeFile(share_name, remote_path, file_obj) # storeFileメソッドを使用してファイルをアップロード
        print(f"Updated remote file: {remote_path}")

def update_local_file(conn, local_path, remote_path, share_name):
    """
    リモートファイルをローカルに更新。
    """
    with open(local_path, 'wb') as file_obj:
        conn.retrieveFile(share_name, remote_path, file_obj) # retrieveFileメソッドを使用してファイルをダウンロード
        print(f"Updated local file: {local_path}")


def sync_directories(conn, local_dir, remote_dir, share_name):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
        print(f"Created local directory: {local_dir}")

    local_items = {item: os.path.join(local_dir, item) for item in os.listdir(local_dir) if os.path.isdir(os.path.join(local_dir, item)) or os.path.isfile(os.path.join(local_dir, item))}
    remote_items = conn.listPath(share_name, remote_dir)
    
    # リモートディレクトリとファイルを分離
    remote_directories = [item.filename for item in remote_items if item.isDirectory and item.filename not in ['.', '..']]
    remote_files = {item.filename: item.last_write_time for item in remote_items if not item.isDirectory}

    # 1 & 2: ローカルにないリモートのディレクトリ/ファイルをローカルに作成/更新
    for item in remote_items:
        if item.filename not in ['.', '..']:
            remote_path = os.path.join(remote_dir, item.filename).replace('\\', '/')
            local_path = os.path.join(local_dir, item.filename)

            if item.isDirectory:
                if not os.path.exists(local_path):
                    os.makedirs(local_path)
                    print(f"Created local directory: {local_path}")
                sync_directories(conn, local_path, remote_path, share_name)
            elif not item.isDirectory and not os.path.exists(local_path):
                update_local_file(conn, local_path, remote_path, share_name)

    # 4 & 5: リモートにないローカルのディレクトリ/ファイルをリモートに作成/更新
    for local_name, local_path in local_items.items():
        if local_name == '.DS_Store' or local_name.startswith('._'):
            continue  # Mac OSによるメタデータファイルはスキップ   
        remote_path = os.path.join(remote_dir, local_name).replace('\\', '/')
        if os.path.isdir(local_path) and local_name not in remote_directories:
            conn.createDirectory(share_name, remote_path)
            sync_directories(conn, local_path, remote_path, share_name)
        elif os.path.isfile(local_path) and local_name not in remote_files:
            update_remote_file(conn, local_path, remote_path, share_name)

    # 3 & 6: ファイル更新のチェック
    for local_name, local_path in local_items.items():
        if local_name in remote_files and os.path.isfile(local_path):
            if local_name == '.DS_Store' or local_name.startswith('._'):
                continue  # Mac OSによるメタデータファイルはスキップ    
            local_mtime = os.path.getmtime(local_path)
            remote_mtime = datetime.fromtimestamp(remote_files[local_name]).timestamp()
            remote_path = os.path.join(remote_dir, local_name).replace('\\', '/')

            if local_mtime > remote_mtime and (local_mtime - remote_mtime) > 30:
                update_remote_file(conn, local_path, remote_path, share_name)
                # ローカルファイルの更新日時変更
                os.utime(path=local_path, times=None)
            elif local_mtime < remote_mtime and (remote_mtime - local_mtime) > 30:
                update_local_file(conn, local_path, remote_path, share_name)



def sync():

    server_ip = en_sever_ip.get()  # サーバーのIPアドレス
    username = en_username.get()  # ユーザー名
    password = en_password.get()  # パスワード
    client_machine = subprocess.check_output('hostname').strip().decode()
    server_domain = ''  # ドメインが不要な場合は空白
    local_directory_path = en_local_directory_path.get()
    shared_resource = en_shared_resource.get()  # 共有リソース名
    remote_directory_path = en_remote_directory_path.get()  # ルートディレクトリ、または同期したい特定のパス

    with open(config_path, 'w') as f:
        f.write(f"""
# config.py
SERVER_IP = '{server_ip}'
USERNAME = '{username}'
PASSWORD = '{password}'
CLIENT_MACHINE = '{subprocess.check_output('hostname').strip().decode()}'
SERVER_DOMAIN = ''
LOCAL_DIRECTORY_PATH = r'{local_directory_path}'
SHARED_RESOURCE = '{shared_resource}'
REMOTE_DIRECTORY_PATH = '{remote_directory_path}'
""")


    try:
        # SMBサーバーに接続
        conn = SMBConnection(username, password, client_machine, server_domain, use_ntlm_v2=True)

        # 接続を試みる
        if not conn.connect(server_ip, 445):
            print("接続に失敗しました。")
            lb_msg.config(text="接続に失敗しました。")
        else:
            print("接続に成功しました。")
            lb_msg.config(text="接続に成功しました。")

            shared_resource = 'erina$'  # 共有リソース名
            remote_directory_path = '/'  # ルートディレクトリ、または同期したい特定のパス

            # 同期関数の呼び出し
            sync_directories(conn, local_directory_path, remote_directory_path, shared_resource)
        
    except Exception as e:
        print(f"Error: {e}")
        lb_msg.config(text=f"接続エラー")

    # 接続を切断
    conn.close()

if __name__ == '__main__':
    # 画面の作成
    root = tk.Tk()
    root.title('SMB同期ツール')
    root.geometry('400x400')

    # SEVER_IPラベルの作成
    lb_server_ip = tk.Label(root, text='SERVER_IP')
    lb_server_ip.grid(row=0, column=0, padx=10, pady=10)

    # SEVER_IPテキストボックスの作成
    en_sever_ip = tk.Entry(root)
    en_sever_ip.insert(tk.END, server_ip)
    en_sever_ip.grid(row=0, column=1, padx=10, pady=10)

    # USERNAMEラベルの作成
    lb_username = tk.Label(root, text='USERNAME')
    lb_username.grid(row=1, column=0, padx=10, pady=10)

    # USERNAMEテキストボックスの作成
    en_username = tk.Entry(root)
    en_username.insert(tk.END, username)
    en_username.grid(row=1, column=1, padx=10, pady=10)

    # PASSWORDラベルの作成
    lb_password = tk.Label(root, text='PASSWORD')
    lb_password.grid(row=2, column=0, padx=10, pady=10)

    # PASSWORDテキストボックスの作成
    en_password = tk.Entry(root,show='*')
    en_password.insert(tk.END, password)
    en_password.grid(row=2, column=1, padx=10, pady=10)
    
    # LOCAL_DIRECTORY_PATHラベルの作成
    lb_local_directory_path = tk.Label(root, text='LOCAL_DIRECTORY_PATH')
    lb_local_directory_path.grid(row=3, column=0, padx=10, pady=10)

    # LOCAL_DIRECTORY_PATHテキストボックスの作成
    en_local_directory_path = tk.Entry(root)
    en_local_directory_path.insert(tk.END, local_directory_path)
    en_local_directory_path.grid(row=3, column=1, padx=10, pady=10)

    # SHARED_RESOURCEラベルの作成
    lb_shared_resource = tk.Label(root, text='SHARED_RESOURCE')
    lb_shared_resource.grid(row=4, column=0, padx=10, pady=10)

    # SHARED_RESOURCEテキストボックスの作成
    en_shared_resource = tk.Entry(root)
    en_shared_resource.insert(tk.END, shared_resource)
    en_shared_resource.grid(row=4, column=1, padx=10, pady=10)

    # REMOTE_DIRECTORY_PATHラベルの作成
    lb_remote_directory_path = tk.Label(root, text='REMOTE_DIRECTORY_PATH')
    lb_remote_directory_path.grid(row=5, column=0, padx=10, pady=10)

    # REMOTE_DIRECTORY_PATHテキストボックスの作成
    en_remote_directory_path = tk.Entry(root)
    en_remote_directory_path.insert(tk.END, remote_directory_path)
    en_remote_directory_path.grid(row=5, column=1, padx=10, pady=10)

    # ボタンの作成
    button = tk.Button(root, text='同期', command=sync)
    button.grid(row=6, column=0, padx=10, pady=10)

    # msgラベルの作成
    lb_msg = tk.Label(root, text='')
    lb_msg.grid(row=7, column=0, padx=10, pady=10)

    # 画面をそのまま表示
    root.mainloop()
