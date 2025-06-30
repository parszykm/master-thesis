from locust import HttpUser, task, between
import os
import random

DATA_DIR = "data"

class InvoiceUser(HttpUser):
    wait_time = between(0.5, 2)  

    def on_start(self):
        
        self.images = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    @task
    def upload_invoice(self):
        if not self.images:
            return

        image_path = random.choice(self.images)
        with open(image_path, "rb") as img:
            files = {'image': (os.path.basename(image_path), img, 'image/jpeg')}
            with self.client.post("/process", files=files, catch_response=True) as response:
                if response.status_code == 202:
                    task_id = response.json().get("task_id")
                    if task_id:
                        self.poll_status(task_id)
                else:
                    response.failure(f"Upload failed: {response.status_code}")

    def poll_status(self, task_id):
        for _ in range(5):  
            with self.client.get(f"/status/{task_id}", catch_response=True) as response:
                if response.status_code == 200:
                    status = response.json().get("status")
                    if status == "done":
                        response.success()
                        return
