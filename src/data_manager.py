import json
import os
from typing import Dict, List, Any
from datetime import datetime
from uuid import UUID
from src.models import CanonicalUpgrade

DATA_DIR = "data"
STATE_FILE = os.path.join(DATA_DIR, "state.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "upgrades.json")

class StateManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.cursors: Dict[str, str] = self._load_state()

    def _load_state(self) -> Dict[str, str]:
        if not os.path.exists(STATE_FILE):
            return {}
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
            return {}

    def get_cursor(self, watcher_id: str) -> datetime:
        ts_str = self.cursors.get(watcher_id)
        if ts_str:
            try:
                return datetime.fromisoformat(ts_str)
            except ValueError:
                return None
        return None

    def update_cursor(self, watcher_id: str, timestamp: datetime):
        self.cursors[watcher_id] = timestamp.isoformat()
        self._save_state()

    def _save_state(self):
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.cursors, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")

class OutputManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.upgrades = []
        self.existing_ids = set()
        self._load_upgrades()

    def _load_upgrades(self):
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, 'r') as f:
                    self.upgrades = json.load(f)
                for u in self.upgrades:
                    u_id = u.get('id', f"{u.get('project')}_{u.get('headline')}")
                    self.existing_ids.add(u_id)
            except Exception as e:
                print(f"Error loading existing upgardes: {e}")

    def save_upgrade(self, upgrade: CanonicalUpgrade):
        
        # Check for duplicates by ID (generate ID from project+headline if not present)
        current_id = f"{upgrade.project}_{upgrade.headline}"
        
        # Serialize new upgrade to dict
        upgrade_dict = upgrade.model_dump()
        # Add ID to dict for future
        upgrade_dict['id'] = current_id
        
        # Ensure datetimes and UUIDs are serializable
        if isinstance(upgrade_dict.get('timestamp'), datetime):
            upgrade_dict['timestamp'] = upgrade_dict['timestamp'].isoformat()
        if isinstance(upgrade_dict.get('canonical_id'), UUID):
            upgrade_dict['canonical_id'] = str(upgrade_dict['canonical_id'])
        if current_id not in self.existing_ids:
            self.upgrades.append(upgrade_dict)
            self.existing_ids.add(current_id)

    def flush(self):
        # Sort by timestamp descending
        try:
            self.upgrades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(self.upgrades, f, indent=2)
            print(f"Flushed {len(self.upgrades)} upgrades to {OUTPUT_FILE}")
        except Exception as e:
            print(f"Error saving output: {e}")
