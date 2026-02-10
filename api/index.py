import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

# 初始化APP
app = FastAPI(title="钦天门紫微斗数API (防爆兜底版)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class PaipanRequest(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    minute: int = 0
    gender: str = "男"

class ZiWeiEngine:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        
        # 纳音五行局
        self.NAYIN = {
            "甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
            "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
            "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
            "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
            "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
            "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2
        }
        self.SIHUA = {"甲":"廉破武阳","乙":"机梁紫阴","丙":"同机昌廉","丁":"阴同机巨","戊":"贪阴右机",
                      "己":"武贪梁曲","庚":"阳武阴同","辛":"巨阳曲昌","壬":"梁紫左武","癸":"破巨阴贪"}

    # 安紫微星
    def get_ziwei_idx(self, bureau, day):
        for x in range(bureau):
            if (day + x) % bureau == 0:
                q = (day + x) // bureau
                base = (2 + q - 1) % 12
                return (base - x) % 12 if x % 2 != 0 else (base + x) % 12
        return 2

    # 安辅星
    def get_aux_stars(self, month_idx, h_idx, y_zhi, y_gan):
        stars = {z: [] for z in self.ZHI}
        
        # 1. 文昌、文曲
        stars[self.ZHI[(10 - h_idx) % 12]].append("文昌")
        stars[self.ZHI[(4 + h_idx) % 12]].append("文曲")
        
        # 2. 左辅、右弼
        stars[self.ZHI[(4 + month_idx - 1) % 12]].append("左辅")
        stars[self.ZHI[(10 - (month_idx - 1)) % 12]].append("右弼")
        
        # 3. 天魁、天钺
        kui_yue = {
            "甲":["丑","未"], "乙":["子","申"], "丙":["亥","酉"], "丁":["亥","酉"],
            "戊":["丑","未"], "己":["子","申"], "庚":["丑","未"], "辛":["午","寅"],
            "壬":["卯","巳"], "癸":["卯","巳"]
        }
        if ky := kui_yue.get(y_gan, []):
            stars[ky[0]].append("天魁"); stars[ky[1]].append("天钺")
            
        # 4. 禄存、擎羊、陀罗
        lu_map = {"甲":"寅","乙":"卯","丙":"巳","丁":"午","戊":"巳","己":"午","庚":"申","辛":"酉","壬":"亥","癸":"子"}
        if y_gan in lu_map:
            lu_idx = self.ZHI.index(lu_map[y_gan])
            stars[self.ZHI[lu_idx]].append("禄存")
            stars[self.ZHI[(lu_idx+1)%12]].append("擎羊")
            stars[self.ZHI[(lu_idx-1)%12]].append("陀罗")
            
        # 5. 火星、铃星
        if y_zhi in "申子辰": start_h, start_l = 2, 10
        elif y_zhi in "寅午戌": start_h, start_l = 1, 3
        elif y_zhi in "亥卯未": start_h, start_l = 9, 10
        else: start_h, start_l = 3, 10
        stars[self.ZHI[(start_h + h_idx) % 12]].append("火星")
        stars[self.ZHI[(start_l + h_idx) % 12]].append("铃星")
        
        # 6. 地劫、地空
        stars[self.ZHI[(11 + h_idx) % 12]].append("地劫")
        stars[self.ZHI[(11 - h_idx) % 12]].append("地空")
        
        # 7. 杂曜
        stars[self.ZHI[(9 + month_idx - 1) % 12]].append("天刑")
        stars[self.ZHI[(1 + month_idx - 1) % 12]].append("天姚")
        y_idx = self.ZHI.index(y_zhi)
        luan_idx = (3 - y_idx) % 12
        stars[self.ZHI[luan_idx]].append("红鸾")
        stars[self.ZHI[(luan_idx + 6) % 12]].append("天喜")
        
        return stars

    def calculate(self, y_gz, m_idx, day, h_idx, gender):
        y_gan, y_zhi = y_gz[0], y_gz[1]
        
        # 1. 命身宫
        ming_idx = (2 + (m_idx - 1) - h_idx) % 12
        shen_idx = (2 + (m_idx - 1) + h_idx) % 12
        
        # 2. 宫干
        start_gan_idx = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan_idx+i)%10] for i in range(12)}
        
        # 3. 定局
        ming_gz = stems[self.ZHI[ming_idx]] + self.ZHI[ming_idx]
        bureau = self.NAYIN.get(ming_gz, 3)
        
        # 4. 安主星
        zw_idx = self.get_ziwei_idx(bureau, day)
        tf_idx = (4 - zw_idx) % 12
        
        stars = {z: [] for z in self.ZHI}
        for n, o in [("紫微",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
            
        # 5. 安辅星
        aux_stars = self.get_aux_stars(m_idx, h_idx, y_zhi, y_gan)
        for z, slist in aux_stars.items(): stars[z].extend(slist)
        
        # 6. 逆布十二宫 & 组装
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        is_yang_year = y_gan in "甲丙戊庚壬"
        direction = 1 if (is_yang_year and gender == "男") or (not is_yang_year and gender == "女") else -1
        sihua_str = self.SIHUA.get(y_gan, "")
        sihua_map = {"禄":sihua_str[0],"权":sihua_str[1],"科":sihua_str[2],"忌":sihua_str[3]}
        
        res_data = {}
        for i, name in enumerate(p_names):
            curr_idx = (ming_idx - i) % 12
            zhi = self.ZHI[curr_idx]
            gan = stems[zhi]
            
            star_list = stars[zhi]
            fmt_stars = []
            for s in star_list:
                tag = ""
                for k, v in sihua_map.items():
                    if v == s: 
                        tag = f"({k})"
                        break
                fmt_stars.append(f"{s}{tag}")
            
            step = i if direction == 1 else (12 - i) % 12
            age_start = bureau + step * 10
            
            tag_list = []
            if gan == y_gan: tag_list.append("【来因宫】")
            if curr_idx == shen_idx: tag_list.append("【身宫】")
            
            # --- 核心兼容性修复 ---
            res_data[name] = {
                "干支": f"{gan}{zhi}",  # 机器人最看重的字段
                "星曜": fmt_stars if fmt_stars else ["【空宫】"],
                "大限": f"{age_start}-{age_start+9}",
                "标注": " ".join(tag_list)
            }
            
        return {
            "局数": f"{bureau}局",
            "核心": {"命宫": self.ZHI[ming_idx], "来因": y_gan},
            "数据": res_data
        }

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc(req: PaipanRequest):
    try:
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        
        # --- 危险操作加固 ---
        try:
            # 尝试获取节气月（干支月）
            m_gz = l.getMonthInGanZhi() # 可能返回 "丙辰"
            zhi = m_gz[1] # 取 "辰"
            m_zhi_idx = engine.ZHI.index(zhi) # 查索引
            m_idx = (m_zhi_idx - 2) % 12 + 1 # 换算成月份数 (寅=1)
        except Exception:
            # 如果干支转换崩了，立刻回退到普通农历月份，保证有盘可排
            m_idx = abs(l.getMonth())
        
        # 闰月霸权：如果是闰月，强制使用农历月份数 (Qi的案例)
        if l.getMonth() < 0: 
            m_idx = abs(l.getMonth())
            
        h_idx = engine.ZHI.index(l.getTimeZhi())
        
        data = engine.calculate(l.getYearGanZhi(), m_idx, l.getDay(), h_idx, req.gender)
        
        lunar_str = f"{l.getYear()}年{abs(l.getMonth())}月{l.getDay()}日"
        if l.getMonth() < 0: lunar_str = "闰" + lunar_str
        
        # --- 双通道返回 ---
        # 无论机器人查 chart 还是 result，都有数据，防止字段缺失报错
        response_payload = {
            "meta": {
                "公历": s.toYmdHms(), 
                "农历": lunar_str,
                "干支": f"{l.getYearInGanZhi()} {l.getMonthInGanZhi()} {l.getDayInGanZhi()}"
            }, 
            "chart": data,  # 旧机器人爱用的 key
            "result": data  # 新标准 key
        }
        return response_payload

    except Exception as e:
        # 万一还是崩了，返回一个 JSON 格式的错误，而不是 500 HTML，方便调试
        return {
            "error": "calculation_failed",
            "message": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
