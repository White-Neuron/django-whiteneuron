from django.utils.translation import gettext_lazy as _
import openai

from dotenv import load_dotenv
import os
import json

load_dotenv()


OPEN_AI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPEN_AI_API_KEY:
    client = openai.Client(api_key=OPEN_AI_API_KEY)
else:
    client = None


def gpt_translate_vi(request, obj):
    """
    GPT translate for LoincTableCore to Vietnamese
    params:
    - request: HttpRequest
    - object_id: int - id of LoincTableCore object
    return:
    - Dict - {"success": bool,
              "message": str,
              "object_id": int - id of LoincTableCore object
              "result": { # All of fields in translation.py of LoincTableCore
                "..._vi": str - Vietnamese translation,
                ...
              }

    """

    # Superuser check
    if not request.user.is_superuser:
        return {"success": False, "message": _("You must be a superuser to use this action"), "object_id": obj.id, "result": {}}

    def translate(obj):
        if not client:
            print("OpenAI API key not found")
            return {
                "success": False,
                "message": _("OpenAI API key not found"),
                "object_id": obj.id,
                "result": {},
            }
        prompt = ""
        obj_data = obj.__dict__
        fields= []
        for field in obj_data:
            if field.endswith("_en"):
                prompt+= f"{field}: {obj_data[field]}\n"
                fields.append(field)
        prompt+= "Hãy dịch tất cả các trường thông tin đuôi \"_vi\" (Tiếng Việt) dựa theo trường đôi \"_en\" (Tiếng Anh). Translate the following JSON, and return the same format with the value translated to Vietnamese (not the key) and nothing else. If the key ends with \"_en\", replace it with \"_vi\"."
        # print(prompt)
        response = client.chat.completions.create(
            model=os.getenv("GPT_MODEL"),
            messages=[
                {"role": "user",
                 "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        # print(content)
        if content.startswith("```json\n"):
            content = content[8:-3]
        content = json.loads(content)

        # post check
        for field in fields:
            if field.replace("_en", "_vi") not in content:
                raise Exception(f"Field {field} not found in GPT response")
        # print(content)
        return content

    try:
        loinc_trans = translate(obj)
    except Exception as e:
        return {"success": False, "message": _("Translate failed: %s") % str(e), "object_id": obj.id, "result": {}}
    return {"success": True, "message": _("Translate successfully"), "object_id": obj.id, "result": loinc_trans}