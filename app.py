'''
Author: DerrickMao maowk56079@gildata.com
Date: 2026-04-12 20:00:50
LastEditors: DerrickMao maowk56079@gildata.com
LastEditTime: 2026-04-12 20:02:00
FilePath: /结构化抽取接口样例/app.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from fastapi import FastAPI
 
app = FastAPI()
 
@app.get("/")
def read_root():
    return {"Python": "on Vercel"}