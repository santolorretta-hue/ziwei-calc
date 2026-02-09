import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="钦天门紫微斗数API (终极修正版)")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PaipanRequest(BaseModel):
    year: int; month: int; day: int; hour: int; minute: int = 0; gender: str = "男"

class ZiWeiEngine:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        # 纳音定局 (命宫干支 -> 局数)
        self.NAYIN = {"甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
                      "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
                      "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
                      "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
                      "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
                      "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2}
        # 钦天四化
        self.SIHUA = {"甲":"廉破武阳","乙":"机梁紫阴","丙":"同机昌廉","丁":"阴同机巨","戊":"贪阴右机",
                      "己":"武贪梁曲","庚":"阳武阴同","辛":"巨阳曲昌","壬":"梁紫左武","癸":"破巨阴贪"}

    def get_ziwei_idx(self, bureau, day):
        # 寅宫(2)起
        for x in range(bureau):
            if (day + x) % bureau == 0:
                q = (day + x) // bureau
                base = (2 + q - 1) % 12
                return (base - x) % 12 if x % 2 != 0 else (base + x) % 12
        return 2

    def calculate(self, y_gan, m_idx, day, h_idx, gender):
        # 1. 命宫定位 (核心修复：直接相减，不再额外偏移)
        # 逻辑：月支代表太阳过宫，时支代表地平旋转。直接差值即为命宫。
        ming_idx = (m_idx - h_idx) % 12
        shen_idx = (m_idx + h_idx) % 12
        
        # 2. 宫干 (五虎遁: 癸年起甲寅)
        start_gan_idx = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan_idx+i)%10] for i in range(12)}
        
        # 3. 定局 (辛酉 -> 木三局)
        ming_gz = stems[self.ZHI[ming_idx]] + self.ZHI[ming_idx]
        bureau = self.NAYIN.get(ming_gz, 3)
        
        # 4. 安星
        zw_idx = self.get_ziwei_idx(bureau, day)
        tf_idx = (4 - zw_idx) % 12
        
        stars = {z: [] for z in self.ZHI}
        
        # 紫微系 (逆行)
        for n, o in [("紫微",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        # 天府系 (顺行)
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
        
        # 5. 逆布十二宫
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        is_yang = y_gan in "甲丙戊庚壬"
        direction = 1 if (is_yang == (gender == "男")) else -1
        
        sihua_str = self.SIHUA.get(y_gan, "")
        sihua_map = {"禄":sihua_str[0],"权":sihua_str[1],"科":sihua_str[2],"忌":sihua_str[3]}
        
        res_data = {}
        for i, name in enumerate(p_names):
            # 逆时针排布
            curr_idx = (ming_idx - i) % 12
            zhi = self.ZHI[curr_idx]
            gan = stems[zhi]
            
            # 组装星曜 + 四化
            star_list = stars[zhi]
            fmt_stars = []
            if not star_list:
                fmt_stars.append("【空宫】")
            else:
                for s in star_list:
                    tag = next((f"({k})" for k, v in sihua_map.items() if v in s), "")
                    fmt_stars.append(f"{s}{tag}")
            
            # 大限
            step = (curr_idx - ming_idx) % 12 if direction == 1 else (ming_idx - curr_idx) % 12
            age = bureau + step * 10
            
            # 标注
            tag_list = []
            if gan == y_gan: tag_list.append("【来因宫】")
            if curr_idx == shen_idx: tag_list.append("【身宫】")
            
            res_data[name] = {
                "干支": f"{gan}{zhi}",
                "星曜": fmt_stars,
                "大限": f"{age}-{age+9}",
                "标注": " ".join(tag_list)
            }
            
        return {"局数": f"{bureau}局", "核心": {"命宫": self.ZHI[ming_idx], "来因": y_gan}, "数据": res_data}

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc(req: PaipanRequest):
    try:
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        
        # 核心修复：直接获取干支月索引 (寅=2, 卯=3, 辰=4)
        m_gz = l.getMonthInGanZhi()
        m_idx = engine.ZHI.index(m_gz[1]) 
        h_idx = engine.ZHI.index(l.getTimeZhi())
        
        data = engine.calculate(l.getYearGan(), m_idx, l.getDay(), h_idx, req.gender)
        return {"meta": {"日期": s.toYmdHms(), "干支": f"{l.getYearInGanZhi()} {m_gz} {l.getDayInGanZhi()}"}, "result": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
