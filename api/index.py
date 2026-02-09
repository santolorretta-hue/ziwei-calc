import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="钦天门紫微斗数API (终极校准版)")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PaipanRequest(BaseModel):
    year: int; month: int; day: int; hour: int; minute: int = 0; gender: str = "男"

class ZiWeiEngine:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        # 纳音五行局 (命宫干支 -> 局数)
        self.NAYIN = {"甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
                      "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
                      "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
                      "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
                      "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
                      "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2}

    def get_ziwei_idx(self, bureau, day):
        # 经典排盘公式: (Day + X) / Bureau = Q
        for x in range(bureau):
            if (day + x) % bureau == 0:
                q = (day + x) // bureau
                base = (2 + q - 1) % 12 # 寅宫(2)起
                return (base - x) % 12 if x % 2 != 0 else (base + x) % 12
        return 2

    def calculate(self, y_gan, m_idx, day, h_idx, gender):
        # 1. 命宫定位 (严格公式)
        # 命宫 = 寅宫(2) + 月份 - 时辰
        ming_idx = (2 + m_idx - h_idx) % 12
        shen_idx = (2 + m_idx + h_idx) % 12
        
        # 2. 宫干 (五虎遁)
        start_gan_idx = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan_idx+i)%10] for i in range(12)}
        
        # 3. 五行局 (纳音)
        ming_gz = stems[self.ZHI[ming_idx]] + self.ZHI[ming_idx]
        bureau = self.NAYIN.get(ming_gz, 3)
        
        # 4. 安星
        zw_idx = self.get_ziwei_idx(bureau, day)
        stars = {z: [] for z in self.ZHI}
        
        # 紫微系 (逆行)
        for n, o in [("紫微",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        # 天府系 (顺行，相对于紫微对称)
        tf_idx = (4 - zw_idx) % 12
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
            
        # 5. 顺逆起大限
        direction = 1 if (y_gan in "甲丙戊庚壬") == (gender == "男") else -1
        
        # 6. 十二宫逆行排列
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        res_data = {}
        for i, name in enumerate(p_names):
            curr_idx = (ming_idx - i) % 12
            zhi = self.ZHI[curr_idx]
            gan = stems[zhi]
            step = (curr_idx - ming_idx) % 12 if direction == 1 else (ming_idx - curr_idx) % 12
            age = bureau + step * 10
            
            tags = []
            if gan == y_gan: tags.append("【来因】")
            if curr_idx == shen_idx: tags.append("【身宫】")
            
            res_data[name] = {
                "宫位": f"{gan}{zhi}",
                "星曜": stars[zhi],
                "大限": f"{age}-{age+9}",
                "标注": " ".join(tags)
            }
        return {"局数": f"{bureau}局", "宫位": self.ZHI[ming_idx], "详情": res_data}

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc(req: PaipanRequest):
    try:
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        # 核心：使用干支月 (辰月=3, 卯月=2)
        m_gz = l.getMonthInGanZhi()
        m_idx = engine.ZHI.index(m_gz[1]) - 1 # 辰月索引为3
        h_idx = engine.ZHI.index(l.getTimeZhi())
        
        data = engine.calculate(l.getYearGan(), m_idx, l.getDay(), h_idx, req.gender)
        return {"meta": {"农历": f"{l.getYearInGanZhi()} {m_gz} {l.getDayInGanZhi()}"}, "result": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
