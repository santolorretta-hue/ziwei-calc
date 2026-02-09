import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="钦天门紫微斗数API (经纬度与节气对齐版)")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PaipanRequest(BaseModel):
    year: int; month: int; day: int; hour: int; minute: int = 0; gender: str = "男"

class ZiWeiEngine:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        # 纳音定局：根据命宫干支查局
        self.NAYIN = {"甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
                      "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
                      "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
                      "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
                      "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
                      "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2}

    def get_ziwei_idx(self, bureau, day):
        # 核心算法：(日 + X) / 局 = 商，由商定紫微位置
        for x in range(bureau):
            if (day + x) % bureau == 0:
                q = (day + x) // bureau
                # 寅宫起步，商数顺行，X数奇减偶加
                base_idx = (2 + q - 1) % 12
                return (base_idx - x) % 12 if x % 2 != 0 else (base_idx + x) % 12
        return 2

    def calculate(self, y_gan, m_idx, day, h_idx, gender):
        # 1. 确定命宫 (寅起正月顺数月，逆数时)
        # 4月6日过清明按3月算：(2 + 3 - 1 - h_idx)
        ming_idx = (2 + (m_idx - 1) - h_idx) % 12
        shen_idx = (2 + (m_idx - 1) + h_idx) % 12
        
        # 2. 五虎遁定宫干 (癸年起甲寅)
        start_gan_idx = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan_idx+i)%10] for i in range(12)}
        
        # 3. 局数：辛酉纳音为木，即木三局
        ming_gz = stems[self.ZHI[ming_idx]] + self.ZHI[ming_idx]
        bureau = self.NAYIN.get(ming_gz, 3)
        
        # 4. 安紫微 (16日木三局 -> 酉位)
        zw_idx = self.get_ziwei_idx(bureau, day)
        stars = {z: [] for z in self.ZHI}
        
        # 紫微系与天府系 (天府与紫微在寅申轴线对称)
        for n, o in [("紫微",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        
        tf_idx = (4 - zw_idx) % 12
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
            
        # 5. 十二宫逆时针排列
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        is_yang = y_gan in "甲丙戊庚壬"
        direction = 1 if (is_yang == (gender == "男")) else -1
        
        res = {}
        for i, name in enumerate(p_names):
            curr_idx = (ming_idx - i) % 12
            zhi = self.ZHI[curr_idx]
            gan = stems[zhi]
            # 计算大限
            step = (curr_idx - ming_idx) % 12 if direction == 1 else (ming_idx - curr_idx) % 12
            age_start = bureau + step * 10
            
            tags = []
            if gan == y_gan: tags.append("【来因】")
            if curr_idx == shen_idx: tags.append("【身宫】")
            
            res[name] = {"干支":f"{gan}{zhi}","星曜":stars[zhi],"大限":f"{age_start}-{age_start+9}","标注":" ".join(tags)}
            
        return {"五行局": f"{bureau}局", "排盘": res}

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc_api(req: PaipanRequest):
    try:
        # 输入默认视为北京时间，若需极其精确，建议用户输入经纬度校准后的“真太阳时”
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        
        # 关键：根据“节气”确定排盘月份索引（寅1, 卯2, 辰3...）
        # 2023-04-06 属于丙辰月，月份索引应为 3
        m_pillar = l.getMonthInGanZhi()
        month_idx = engine.ZHI.index(m_pillar[1]) - 1 # 辰(4) - 寅(2) + 1 = 3
        
        # 调用引擎
        data = engine.calculate(l.getYearGan(), month_idx, l.getDay(), engine.ZHI.index(l.getTimeZhi()), req.gender)
        return {"meta": {"公历": s.toYmdHms(), "干支": f"{l.getYearInGanZhi()} {m_pillar} {l.getDayInGanZhi()}"}, "result": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
