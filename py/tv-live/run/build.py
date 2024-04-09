import re, requests, chardet, os, ast, json, socket, urllib.parse
import concurrent.futures
from pypinyin import lazy_pinyin
from pathlib import Path
from urllib.parse import urlparse


class Playlist:

    def build_playlist(self):
        self.__read_options__()
        self.variables["urls"] = self.read_urls("./urls.txt")
        self.variables["unwanted_keys"] = self.read_csv("./black.txt")
        self.variables["rename_rules"] = self.read_rename_rules("./rename.txt")
        if self.variables["switch_download"] == "on":
            self.__download_from_urls__()
        self.__build_input_file_list__()
        self.__load_from_files__()
        if self.variables["switch_ipv4_6_46"] == 4:
            self.__filter_v4_channels__()
        elif self.variables["switch_ipv4_6_46"] == 6:
            self.__filter_v6_channels__()
        elif self.variables["switch_ipv4_6_46"] == 46:
            pass
        self.__delete_unwanted_items__()
        self.__rename_channels__(self.variables["rename_rules"])
        self.__rename_channels__(self.variables["rename_rules"])
        self.__rename_channels__(self.variables["rename_rules"])
        if self.variables["switch_connectivity_check"] == "on":
            self.__get_playable_channels__()
        self.__sort_channels__()
        self.__save_playlists__()

    def __init__(self):
        self.variables = {
            "download_folder": "../download",
            "output_folder": "../../../tv",
            "max_workers": 30,
            "output_file_name": "channels",
            "priority_name_keys": ["湖北卫视", "湖南卫视", "凤凰","CHC"],
            "priority_url_keys": ["[", "chinamobile"],
            "switch_connectivity_check": "on",
            "switch_download": "on",
            "switch_ipv4_6_46": 6,
        }
        self.channels = {}

    def read_urls(self, filename):
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as file:
                lines = file.read().splitlines()
            lines = [
                line.replace(",", "")
                for line in lines
                if line.startswith(("http://", "https://"))
            ]
            unique_lines = list(set(lines))
            sorted_lines = sorted(
                unique_lines, key=lambda x: x[x.index("://") :].lower()
            )
            with open(filename, "w", encoding="utf-8") as file:
                for line in sorted_lines:
                    file.write(line + "\n")
            return sorted_lines
        else:
            print(f"{filename} does not exist.")
            return None

    def read_csv(self, filename):
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as file:
                lines = file.read().replace("\n", ",").split(",")
            lines = [line.strip() for line in lines if line.strip() != ""]
            unique_lines = list(set(lines))
            sorted_lines = sorted(unique_lines, key=lambda x: x.lower())
            with open(filename, "w", encoding="utf-8") as file:
                for i in range(0, len(sorted_lines), 8):
                    file.write(", ".join(sorted_lines[i : i + 8]) + "\n")
            return sorted_lines
        else:
            print(f"{filename} does not exist.")
            return None

    def read_rename_rules(self, file_path):
        # Read the file and convert each line into a list item
        with open(file_path, "r", encoding="utf-8") as f:
            data = [ast.literal_eval(line.strip()) for line in f]

        # Remove duplicates while preserving order
        seen = set()
        data = [
            item for item in data if not (tuple(item) in seen or seen.add(tuple(item)))
        ]

        # Overwrite the original file with deduplicated data
        with open(file_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(str(item) + "\n")

        # Return the deduplicated data
        return data

    def __download_from_urls__(self):
        if "检查下载目录是否存在, 不存在就创建.":
            path = Path(self.variables["download_folder"])
            if not path.exists():
                path.mkdir(parents=True)
                self.variables["download_folder"] = path

        input("请开启VPN, 按enter键继续.")
        for url in self.variables["urls"]:
            print(f"下载 {url} ... ", end="")
            parsed_url = urlparse(url)
            domain_and_path = parsed_url.netloc + parsed_url.path.rsplit("/", 1)[0]
            domain_and_path = domain_and_path.replace(".", ".").replace("/", "_")
            file_name = url.split("/")[-1]
            if not file_name or "?" in file_name or "&" in file_name:
                file_name = domain_and_path + ".txt"
            else:
                file_name = domain_and_path + "_" + file_name
            path = Path(self.variables["download_folder"]) / file_name
            try:
                response = requests.get(url)
            except requests.exceptions.ConnectionError:
                print(f"从 {url} 失败")
                continue
            encoding = chardet.detect(response.content)["encoding"]
            if not encoding:
                encoding = "utf-8"
            try:
                content = response.content.decode(encoding)
            except UnicodeDecodeError:
                content = response.content.decode("utf-8")
            content = content.encode("utf-8")
            with open(path, "wb") as f:
                f.write(content)
            print(f"完成\n")
        return

    def __build_input_file_list__(self):
        pathList = list(Path(self.variables["download_folder"]).glob("*"))
        self.input_file_list = {str(filePath) for filePath in pathList}
        print("找到如下文件:")
        for file in self.input_file_list:
            print(f"{file.split(f'{os.sep}')[-1]}")
        print()

    def __load_from_files__(self):
        if type(self.input_file_list).__name__ == "str":
            self.input_file_list = [self.input_file_list]
        count = 0
        phenix_channels = {}
        success = False
        for file in self.input_file_list:
            content = ""
            try:
                rawdata = open(file, "rb").read()
                result = chardet.detect(rawdata)
                encoding = result.get("encoding", "utf-8")
                try:
                    with open(file, "r", encoding=encoding) as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file, "r", encoding="utf-8") as f:
                        content = f.read()
                count += 1
                success = True
            except Exception as e:
                print(f"处理文件 {file} 时出错: {str(e)}")
                continue

            lines = content.split("\n")
            for i in range(len(lines)):
                if "http" in lines[i]:
                    http_index = lines[i].index("http")
                    if http_index > 1 and lines[i][:http_index].strip()[-1] == ",":
                        name = lines[i][: http_index - 1].strip()
                        address = lines[i][http_index:].strip()
                        self.channels[address] = name
                    elif i > 0 and lines[i - 1].startswith("#EXTINF"):
                        name = lines[i - 1].split(",")[-1].strip()
                        address = lines[i].strip()
                        self.channels[address] = name

        if not success:
            print("没有建立频道列表,所有文件都处理失败.")
            return
        print("从 {} 个文件中获取了 {} 个频道.\n".format(count, len(self.channels)))

        # 写phenix.txt
        for address, name in self.channels.items():
            if (
                "凤凰香港" in name
                or "凤凰中文" in name
                or "凤凰资讯" in name
                or "鳳凰" in name
            ):
                phenix_channels[address] = name
        phenix_channels = dict(
            sorted(
                phenix_channels.items(),
                key=lambda item: self.__build_sort_key__(item),
            )
        )
        with open(
            self.variables["output_folder"] + "/phenix.txt", "w", encoding="utf-8"
        ) as fw:
            for address, name in phenix_channels.items():
                fw.write(name + "," + address + "\n")

        print(
            str(len(phenix_channels))
            + f" 播放地址写入了{self.variables['output_folder']}/phenix.txt\n"
        )

    def __filter_v4_channels__(self):
        v4_channels = {}
        for address, name in self.channels.items():
            if "[" not in address and "]" not in address:
                v4_channels[address] = name

        print(
            "从 {} 个频道中筛选出 {} 个IPv4频道.\n".format(
                len(self.channels), len(v4_channels)
            )
        )
        self.channels = v4_channels

    def __filter_v6_channels__(self):
        v6_channels = {}
        for address, name in self.channels.items():
            if (
                self.is_ipv6(address)
                # "[" in address
                # and "]" in address
                or "凤凰|鳳凰" in name
                # or "mobaibox.com" in address.lower()
                or "chinamobile" in address.lower()
                or "cmvideo" in address.lower()
            ):
                v6_channels[address] = name

        print(
            "从 {} 个频道中筛选出 {} 个IPv6频道.\n".format(
                len(self.channels), len(v6_channels)
            )
        )
        self.channels = v6_channels

    def __rename_channels__(self, rename_rules):
        for rename_rule in rename_rules:
            # print(rename_rule)
            pattern = re.compile(rename_rule[0], re.I)
            for address, name in self.channels.items():
                if pattern.search(name):
                    self.channels[address] = pattern.sub(rename_rule[1], name)

    def __delete_unwanted_items__(self):
        total_num = len(self.channels)
        if not self.variables["unwanted_keys"] or all(
            item.strip() == "" for item in self.variables["unwanted_keys"]
        ):
            return self.channels
        items_to_delete = [
            address
            for address, name in self.channels.items()
            if any(
                unwanted_channel in name or unwanted_channel in address
                for unwanted_channel in self.variables["unwanted_keys"]
                if unwanted_channel.strip() != ""
            )
        ]
        for item in items_to_delete:
            del self.channels[item]
        print(
            "删除了 {} 个频道, 还有 {} 个频道.\n".format(
                total_num - len(self.channels), len(self.channels)
            )
        )

    def __check_url_connectivity__(self, url):
        try:
            response = requests.get(url, stream=True, timeout=1)
            return url, response.status_code == 200
        except requests.exceptions.RequestException:
            return url, False

    def __get_playable_channels__(self):
        input("请关闭VPN, 按enter键继续.")
        print("\n检查频道是否可以播放, 请稍后 ...")
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=int(self.variables["max_workers"])
        ) as executor:
            future_to_url = {
                executor.submit(self.__check_url_connectivity__, url): url
                for url in self.channels.keys()
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    url, can_connect = future.result()
                except Exception as exc:
                    print("%r generated an exception: %s" % (url, exc))
                else:
                    if not can_connect:
                        del self.channels[url]

    def __build_sort_key__(self, channel_tuple):
        address = channel_tuple[0]
        name = channel_tuple[1]

        ip_priority = 99
        channel_choice_num = 99

        for ip_str in self.variables["priority_url_keys"]:
            if ip_str in address:
                ip_priority = self.variables["priority_url_keys"].index(ip_str)

        for channel_str in self.variables["priority_name_keys"]:
            if channel_str in name:
                channel_choice_num = self.variables["priority_name_keys"].index(
                    channel_str
                )
        if re.match(r"CCTV\d{1,2}(?![+a-zA-Z])", name):
            parts = re.split(r"(\d+)", name)
            parts[1::2] = map(int, parts[1::2])
            return [channel_choice_num] + parts + [str(ip_priority)]
        else:
            return [channel_choice_num] + lazy_pinyin(name) + [str(ip_priority)]

    def __sort_channels__(self):
        english_channels = {
            k: v
            for k, v in self.channels.items()
            if re.match(r"CCTV\d{1,2}(?![+a-zA-Z])", v)
        }
        non_english_channels = {
            k: v
            for k, v in self.channels.items()
            if not re.match(r"CCTV\d{1,2}(?![+a-zA-Z])", v)
        }

        # 对每部分进行排序
        sorted_english_channels = dict(
            sorted(
                english_channels.items(),
                key=lambda item: self.__build_sort_key__(item),
            )
        )
        sorted_non_english_channels = dict(
            sorted(
                non_english_channels.items(),
                key=lambda item: self.__build_sort_key__(item),
            )
        )

        # 将两部分合并
        sorted_channels = {**sorted_english_channels, **sorted_non_english_channels}
        print(f'对 {len(sorted_channels)} 个频道 按 "名称" 进行了总排序.\n')
        self.channels = sorted_channels

    def __save_playlists__(self):
        filename = (
            self.variables["output_folder"]
            + "/"
            + self.variables["output_file_name"]
            + ".txt"
        )
        # CCTV1~CCTV17
        grouped_channels = {}
        cctv_channels = {
            url: name
            for url, name in self.channels.items()
            if re.match(r"CCTV(?!\d+[+a-zA-Z])", name)
        }
        grouped_channels.update(cctv_channels)

        # 优选频道
        favorite_channels = {
            url: name
            for url, name in self.channels.items()
            if re.match(r"湖北卫视|湖南卫视|凤凰|CHC", name)
            if name not in grouped_channels.values()
        }
        grouped_channels.update(favorite_channels)

        # 综艺
        variety_channels = {
            url: name
            for url, name in self.channels.items()
            if re.match(r".*综艺.*", name)
            if name not in grouped_channels.values()
        }
        grouped_channels.update(variety_channels)

        # 卫视
        satellite_channels = {
            url: name
            for url, name in self.channels.items()
            if re.match(r".*卫视.*", name)
            if name not in grouped_channels.values()
            # if not re.match(r"湖(北|南)卫视", name)
        }
        grouped_channels.update(satellite_channels)

        # 影视
        movie_channels = {
            url: name
            for url, name in self.channels.items()
            if re.search(r"(剧|影|悬疑|中国功夫)", name)
            if name not in grouped_channels.values()
        }
        grouped_channels.update(movie_channels)

        # 动漫
        cartoon_channels = {
            url: name
            for url, name in self.channels.items()
            if re.search(r"(动画|卡通|动漫)", name)
            if name not in grouped_channels.values()
        }
        grouped_channels.update(cartoon_channels)

        # MV
        MV_channels = {
            url: name
            for url, name in self.channels.items()
            if re.search(
                r"(.mp4)|(vodcdn.video.taobao.com)|(bizcommon.alicdn.com)", url
            )
            if url not in grouped_channels.keys()
        }
        grouped_channels.update(MV_channels)

        # 其它
        other_channels = {
            url: name
            for url, name in self.channels.items()
            if name not in grouped_channels.values()
        }
        grouped_channels.update(other_channels)

        # 取唯一频道名, 存为 m3u 文件
        unique_channels = self.__get_unique_channels__(grouped_channels)
        self.__save_to_m3u__(unique_channels)

        # 按分组顺序保存为 txt 文件, 已加入分组名称
        with open(filename, "w", encoding="utf-8") as f:
            f.write("央视,#genre#\n")
            for address, name in cctv_channels.items():
                f.write(f"{name},{address}\n")

            f.write("优选,#genre#\n")
            for address, name in favorite_channels.items():
                f.write(f"{name},{address}\n")
            for address, name in variety_channels.items():
                f.write(f"{name},{address}\n")

            f.write("卫视,#genre#\n")
            for address, name in satellite_channels.items():
                f.write(f"{name},{address}\n")

            f.write("影视,#genre#\n")
            for address, name in movie_channels.items():
                f.write(f"{name},{address}\n")

            f.write("动漫,#genre#\n")
            for address, name in cartoon_channels.items():
                f.write(f"{name},{address}\n")

            f.write("其它,#genre#\n")
            for address, name in other_channels.items():
                f.write(f"{name},{address}\n")

            if MV_channels:
                f.write("MV,#genre#\n")
                for address, name in MV_channels.items():
                    f.write(f"{name},{address}\n")

        print('写入了 {} 个频道到 "{}" 文件\n'.format(len(self.channels), filename))

    def __get_unique_channels__(self, channels):
        unique_channels = {}
        for address, name in channels.items():
            if name not in unique_channels.values():
                unique_channels[address] = name
        return unique_channels

    def __save_to_m3u__(self, channels):
        filename = (
            self.variables["output_folder"]
            + "/"
            + self.variables["output_file_name"]
            + ".m3u"
        )
        with open(filename, "w", encoding="utf-8") as file:
            file.write("#EXTM3U\n")
            for url, name in channels.items():
                file.write(f"#EXTINF:-1,{name}\n")
                file.write(f"{url}\n")
        print('保存了 {} 个频道到 "{}" 文件'.format(len(channels), filename))

    def __read_options__(self):
        if not os.path.exists("options.json"):
            print(
                "配置文件不存在,是否使用默认值创建options.json文件? ('y'/<enter> = 是)",
                end=" ",
            )
            answer = input() or "y"
            if answer.lower() == "y":
                with open("options.json", "w", encoding="utf-8") as f:
                    json.dump(self.variables, f, ensure_ascii=False, indent=4)
                    print("已创建配置文件.")
        else:
            print("发现配置文options.json, 读取配置文件吗? ('y'/<enter> = 是)", end=" ")
            answer = input() or "y"
            if answer.lower() == "y":
                with open("./options.json", "r", encoding="utf-8") as f:
                    content = f.read()
                    config = json.loads(content)
                    self.variables = {k: config[k] for k in sorted(config.keys())}

    def is_ipv6(self, url):
        try:
            # Parse the URL to get the netloc part
            netloc = urllib.parse.urlparse(url).netloc
            # If the netloc part contains square brackets, it's an IPv6 address
            if "[" in netloc and "]" in netloc:
                ip = netloc.split("[")[-1].split("]")[0]
            else:
                ip = netloc.split(":")[0]
            # Try to convert the IP address to an IPv6 address
            socket.inet_pton(socket.AF_INET6, ip)
            return True
        except (socket.gaierror, OSError):
            return False


my_playlist = Playlist()
my_playlist.build_playlist()
