import json
import config

class EditPrompts:
    def __init__(self, json_path: str = config.json_path):
        self.json_path = json_path

    def update_prompt_status(
        self,    
        prompt_id: str,
        ten_cay_trong: str,
        tuoi: int,
        chieu_cao: float,
        do_am: int,
        nhiet_do: float,
        anh_sang: float,
        tinh_trang_la: str,
        toc_do_sinh_truong: str,
        json_path: str = config.json_path
    ) -> str:

        with open(json_path, "r", encoding="utf-8") as f:
            prompts = json.load(f)

        selected = next((p for p in prompts if p["id"] == prompt_id), None)
        if not selected:
            return f"Không tìm thấy prompt với ID: {prompt_id}"

        template = selected["template"]

        filled = template.format(
            ten_cay_trong=ten_cay_trong,
            tuoi=tuoi,
            chieu_cao=chieu_cao,
            do_am=do_am,
            nhiet_do=nhiet_do,
            anh_sang=anh_sang,
            tinh_trang_la=tinh_trang_la,
            toc_do_sinh_truong=toc_do_sinh_truong,
        )

        return filled
    
