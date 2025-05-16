# -*- coding: utf-8 -*-

import sys,os,json,subprocess
parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, 'lib'))
sys.path.append(os.path.join(parent_folder_path, 'plugin'))

from flowlauncher import FlowLauncher


class EdgePaths:
    """Handles discovery of Microsoft Edge executable paths and user profile data paths."""

    USER_DATA_PATH = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data')

    _edge_paths = [
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe')
    ]

    EXECUTABLE_PATH = next((path for path in _edge_paths if os.path.exists(path)), None)


class Result:
    """Represents a result entry for Flow Launcher."""

    def __init__(self, title, subtitle, ico_path, json_rpc_action=None):
        self.title = title
        self.subtitle = subtitle
        self.ico_path = ico_path
        self.json_rpc_action = json_rpc_action

    def to_json(self):
        return {
            "Title": self.title,
            "SubTitle": self.subtitle,
            "IcoPath": self.ico_path,
            "JsonRPCAction": self.json_rpc_action.to_json() if self.json_rpc_action else None
        }


class JsonRPCAction:
    """Defines a JSON RPC action for executing commands through Flow Launcher."""

    def __init__(self, method, parameters):
        self.method = method
        self.parameters = parameters

    def to_json(self):
        return {"method": self.method, "parameters": self.parameters}


class EdgeProfileManager:
    """Manages discovery and launching of Edge profiles."""

    DEFAULT_EDGE_ICON = "Images/app.png"
    ERROR_ICON = "Images/error.png"

    @staticmethod
    def find_profile_icon(profile_path):
        """Finds the profile-specific icon."""
        icon_path = os.path.join(profile_path, "Edge Profile.ico")
        return icon_path if os.path.exists(icon_path) else None

    @staticmethod
    def get_profiles():
        """Discovers Edge profiles and retrieves their names and icons."""
        profiles = []
        profile_name_map = {}

        local_state_path = os.path.join(EdgePaths.USER_DATA_PATH, 'Local State')
        if os.path.exists(local_state_path):
            try:
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                    info_cache = local_state.get('profile', {}).get('info_cache', {})
                    profile_name_map = {directory: info.get('name', directory) for directory, info in info_cache.items()}
            except Exception as e:
                print(f"ERROR: Failed to read Local State: {e}", file=sys.stderr)

        if not os.path.exists(EdgePaths.USER_DATA_PATH):
            return profiles

        try:
            for item in os.listdir(EdgePaths.USER_DATA_PATH):
                item_path = os.path.join(EdgePaths.USER_DATA_PATH, item)
                if os.path.isdir(item_path) and (item.startswith('Profile') or item == 'Default'):
                    profiles.append({
                        'name': profile_name_map.get(item, item),
                        'directory': item,
                        'icon_path': EdgeProfileManager.find_profile_icon(item_path)
                    })
        except Exception as e:
            print(f"ERROR: Failed to list profile directories: {e}", file=sys.stderr)

        return profiles

    @staticmethod
    def launch_profile(profile_directory):
        """Launches Edge using the specified profile."""
        if not EdgePaths.EXECUTABLE_PATH:
            print("ERROR: Edge executable not found.", file=sys.stderr)
            return

        try:
            subprocess.Popen([EdgePaths.EXECUTABLE_PATH, f'--profile-directory={profile_directory}'])
        except Exception as e:
            print(f"ERROR: Failed to launch profile {profile_directory}: {e}", file=sys.stderr)


class EdgeProfilePlugin(FlowLauncher):
    """Handles user queries and manages results."""

    def query(self, query_text):
        results = []

        if not EdgePaths.EXECUTABLE_PATH:
            results.append(Result("Microsoft Edge Not Found", "Could not find msedge.exe.", EdgeProfileManager.ERROR_ICON).to_json())
        else:
            profiles = EdgeProfileManager.get_profiles()
            filtered_profiles = [p for p in profiles if query_text.lower() in p['name'].lower()] if query_text else profiles

            if not filtered_profiles:
                subtitle = f"No Edge profiles match '{query_text}'." if query_text else f"Looked in {EdgePaths.USER_DATA_PATH}."
                results.append(Result("No matching profiles found", subtitle, EdgeProfileManager.DEFAULT_EDGE_ICON).to_json())
            else:
                for profile in filtered_profiles:
                    icon_to_use = profile.get('icon_path') if profile.get('icon_path') and os.path.exists(profile['icon_path']) else EdgeProfileManager.DEFAULT_EDGE_ICON
                    results.append(Result(profile['name'], f"Launch Edge with profile: {profile['name']}", icon_to_use, JsonRPCAction('launch_profile', [profile['directory']])).to_json())

        return results

    def launch_profile(self, profile_directory):
        EdgeProfileManager.launch_profile(profile_directory)


if __name__ == "__main__":
    EdgeProfilePlugin()