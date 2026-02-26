import os
from typing import Dict, List, Any
from datetime import datetime
from uuid import UUID
from dotenv import load_dotenv
from supabase import create_client, Client
from src.models import CanonicalUpgrade

load_dotenv()
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")

# Initialize Supabase client
supabase: Client = create_client(url, key)

class StateManager:
    def __init__(self):
        self.cursors: Dict[str, str] = self._load_state()

    def _load_state(self) -> Dict[str, str]:
        try:
            response = supabase.table('state').select('*').execute()
            data = response.data if response and hasattr(response, 'data') else []
            return {row['id']: row['cursor'] for row in data}
        except Exception as e:
            print(f"Error loading state from Supabase: {e}")
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
        iso_ts = timestamp.isoformat()
        self.cursors[watcher_id] = iso_ts
        try:
            supabase.table('state').upsert({'id': watcher_id, 'cursor': iso_ts}).execute()
        except Exception as e:
            print(f"Error saving state to Supabase: {e}")


class OutputManager:
    def __init__(self):
        self.upgrades = []
        self.existing_ids = set()
        self._load_upgrades()

    def _load_upgrades(self):
        try:
            response = supabase.table('upgrades').select('id').execute()
            data = response.data if response and hasattr(response, 'data') else []
            for row in data:
                self.existing_ids.add(row['id'])
        except Exception as e:
            print(f"Error loading existing upgrades from Supabase: {e}")

    def save_upgrade(self, upgrade: CanonicalUpgrade):
        current_id = f"{upgrade.project}_{upgrade.headline}"
        
        upgrade_dict = upgrade.model_dump()
        upgrade_dict['id'] = current_id
        
        # Ensure payload is JSON serializable
        if isinstance(upgrade_dict.get('timestamp'), datetime):
            upgrade_dict['timestamp'] = upgrade_dict['timestamp'].isoformat()
        if isinstance(upgrade_dict.get('canonical_id'), UUID):
            upgrade_dict['canonical_id'] = str(upgrade_dict['canonical_id'])
            
        if current_id not in self.existing_ids:
            # Map Python dict to Postgres columns
            supabase_row = {
                'id': current_id,
                'project': upgrade.project,
                'timestamp': upgrade_dict.get('timestamp'),
                'payload': upgrade_dict
            }
            self.upgrades.append(supabase_row)
            self.existing_ids.add(current_id)

    def flush(self):
        if not self.upgrades:
            return
            
        try:
            # Upsert the batch to Supabase
            supabase.table('upgrades').upsert(self.upgrades).execute()
            print(f"Flushed {len(self.upgrades)} upgrades to Supabase.")
            # Clear memory after successful flush
            self.upgrades = [] 
        except Exception as e:
            print(f"Error saving output to Supabase: {e}")
