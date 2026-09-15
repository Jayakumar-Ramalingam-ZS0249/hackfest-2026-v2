"""
In-memory upload-job progress tracker.

Deliberately separate from ClaimRepository: a job only exists for as
long as a browser tab is polling that specific upload's progress. It
is never listed, searched, or treated as claim data -- once `done` is
true the caller reads `result` (the real claim record) and moves on.
"""


class UploadJobRepository:
    def __init__(self):
        self._jobs: dict[str, dict] = {}

    def create(self, job_id: str) -> None:
        self._jobs[job_id] = {
            "stage": "queued",
            "label": "Preparing upload…",
            "percent": 0,
            "done": False,
            "error": None,
            "result": None,
        }

    def update(self, job_id: str, *, stage: str, label: str, percent: int) -> None:
        job = self._jobs.get(job_id)
        if job is None or job["done"]:
            return
        job["stage"] = stage
        job["label"] = label
        job["percent"] = percent

    def complete(self, job_id: str, result: dict) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        job["done"] = True
        job["percent"] = 100
        job["stage"] = "done"
        job["result"] = result

    def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        job["done"] = True
        job["error"] = error

    def get(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)


upload_job_repository = UploadJobRepository()
