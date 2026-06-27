import os
import shutil
import datetime

class SnapshotManager:
    def __init__(self, context):
        self.ctx = context
        self.snapshots = []

    def take_snapshot(self, label=""):
        if not self.ctx.cwd:
            return
        backup_root = os.path.join(self.ctx.cwd, ".atlas_snapshots")
        os.makedirs(backup_root, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_root, f"snapshot_{ts}")
        shutil.copytree(self.ctx.cwd, dest, dirs_exist_ok=True)
        self.snapshots.append({"ts": ts, "path": dest, "label": label})
        return dest

    def restore(self, snapshot_id):
        # Find snapshot by id, then shutil.copytree back (not implemented)
        pass
