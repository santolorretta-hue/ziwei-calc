import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="钦天门紫微斗数API (真值校准版)")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class PaipanRequest(BaseModel):
    year: int; month: int; day: int; hour: int; minute: int = 0; gender: str = "男"

class ZiWeiEngine:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        
        # 纳音五行局 (命宫干支 -> 局数)
        self.NAYIN = {
            "甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
            "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
            "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
            "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
            "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
            "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2
        }
        
        # 钦天四化
        self.SIHUA = {"甲":"廉破武阳","乙":"机梁紫阴","丙":"同机昌廉","丁":"阴同机巨","戊":"贪阴右机",
                      "己":"武贪梁曲","庚":"阳武阴同","辛":"巨阳曲昌","壬":"梁紫左武","癸":"破巨阴贪"}

    def get_ziwei_idx(self, bureau, day):
        # 寅(2)起, (Day+X)/Bureau = Q. 
        # R=0: Q+1+2-1. R!=0: Q+1+2-1 +/- (Bureau-R)
        for x in range(bureau):
            if (day + x) % bureau == 0:
                q = (day + x) // bureau
                base = (2 + q - 1) % 12
                # x为奇数减，偶数加
                return (base - x) % 12 if x % 2 != 0 else (base + x) % 12
        return 2

    # 辅助星曜计算
    def get_aux_stars(self, month_idx, h_idx, y_zhi, y_gan):
        stars = {z: [] for z in self.ZHI}
        
        # 1. 昌曲 (时)
        # 文昌: 戌(10) - 时 + 1. 文曲: 辰(4) + 时 - 1
        stars[self.ZHI[(10 - h_idx) % 12]].append("文昌")
        stars[self.ZHI[(4 + h_idx) % 12]].append("文曲")
        
        # 2. 左右 (月)
        # 左辅: 辰(4) + 月 - 1. 右弼: 戌(10) - 月 + 1
        stars[self.ZHI[(4 + month_idx - 1) % 12]].append("左辅")
        stars[self.ZHI[(10 - (month_idx - 1)) % 12]].append("右弼")
        
        # 3. 魁钺 (年干)
        kui_yue = {
            "甲":["丑","未"], "乙":["子","申"], "丙":["亥","酉"], "丁":["亥","酉"],
            "戊":["丑","未"], "己":["子","申"], "庚":["丑","未"], "辛":["午","寅"],
            "壬":["卯","巳"], "癸":["卯","巳"]
        }
        ky = kui_yue.get(y_gan, [])
        if ky:
            stars[ky[0]].append("天魁")
            stars[ky[1]].append("天钺")
            
        # 4. 禄存/羊陀 (年干)
        lu_map = {"甲":"寅","乙":"卯","丙":"巳","丁":"午","戊":"巳","己":"午","庚":"申","辛":"酉","壬":"亥","癸":"子"}
        if y_gan in lu_map:
            lu_idx = self.ZHI.index(lu_map[y_gan])
            stars[self.ZHI[lu_idx]].append("禄存")
            stars[self.ZHI[(lu_idx+1)%12]].append("擎羊")
            stars[self.ZHI[(lu_idx-1)%12]].append("陀罗")
            
        # 5. 火铃 (年支+时支)
        # 申子辰人(寅午戌起), 寅午戌人(丑卯起), 亥卯未人(酉戌起), 巳酉丑人(卯戌起)
        y_group = ""
        if y_zhi in "申子辰": start_h, start_l = 2, 10 # 寅=2, 戌=10
        elif y_zhi in "寅午戌": start_h, start_l = 1, 3 # 丑=1, 卯=3
        elif y_zhi in "亥卯未": start_h, start_l = 9, 10 # 酉=9, 戌=10
        else: start_h, start_l = 3, 10 # 卯=3, 戌=10 (巳酉丑)
        
        stars[self.ZHI[(start_h + h_idx) % 12]].append("火星")
        stars[self.ZHI[(start_l + h_idx) % 12]].append("铃星")
        
        # 6. 空劫 (亥起)
        # 地劫: 亥(11) + 时 - 1. 地空: 亥(11) - 时 + 1
        stars[self.ZHI[(11 + h_idx) % 12]].append("地劫")
        stars[self.ZHI[(11 - h_idx) % 12]].append("地空")
        
        # 7. 其它杂曜 (天刑/天姚/红鸾/天喜)
        # 天刑: 酉(9) + 月 - 1. 天姚: 丑(1) + 月 - 1
        stars[self.ZHI[(9 + month_idx - 1) % 12]].append("天刑")
        stars[self.ZHI[(1 + month_idx - 1) % 12]].append("天姚")
        # 红鸾: 卯(3) - 年支 + 1. 天喜: 对宫
        y_idx = self.ZHI.index(y_zhi)
        luan_idx = (3 - y_idx) % 12
        stars[self.ZHI[luan_idx]].append("红鸾")
        stars[self.ZHI[(luan_idx + 6) % 12]].append("天喜")
        
        return stars

    def calculate(self, y_gz, m_idx, day, h_idx, gender):
        y_gan, y_zhi = y_gz[0], y_gz[1]
        
        # 1. 命宫定位 (寅2 + 月 - 时)
        ming_idx = (2 + (m_idx - 1) - h_idx) % 12
        
        # 身宫 (寅2 + 月 + 时) - 依口诀: 子午命, 丑未福, 寅申官, 卯酉迁, 辰戌财, 巳亥夫
        # 这里用公式算更准:
        shen_idx = (2 + (m_idx - 1) + h_idx) % 12
        
        # 2. 宫干 (五虎遁)
        start_gan_idx = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan_idx+i)%10] for i in range(12)}
        
        # 3. 定局
        ming_gz = stems[self.ZHI[ming_idx]] + self.ZHI[ming_idx]
        bureau = self.NAYIN.get(ming_gz, 3)
        
        # 4. 安星
        zw_idx = self.get_ziwei_idx(bureau, day)
        tf_idx = (4 - zw_idx) % 12
        
        stars = {z: [] for z in self.ZHI}
        
        # 主星
        for n, o in [("紫薇",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
            
        # 辅星
        aux_stars = self.get_aux_stars(m_idx, h_idx, y_zhi, y_gan)
        for z, slist in aux_stars.items():
            stars[z].extend(slist)
        
        # 5. 逆布十二宫
        p_names = ["命宫","兄弟宫","夫妻宫","子女宫","财帛宫","疾厄宫","迁移宫","交友宫","官禄宫","田宅宫","福德宫","父母宫"]
        
        # 大限顺逆: 阳男阴女顺(1), 阴男阳女逆(-1)
        is_yang_year = y_gan in "甲丙戊庚壬"
        direction = 1 if (is_yang_year and gender == "男") or (not is_yang_year and gender == "女") else -1
        
        sihua_str = self.SIHUA.get(y_gan, "")
        sihua_map = {"禄":sihua_str[0],"权":sihua_str[1],"科":sihua_str[2],"忌":sihua_str[3]}
        
        res_data = {}
        for i, name in enumerate(p_names):
            curr_idx = (ming_idx - i) % 12
            zhi = self.ZHI[curr_idx]
            gan = stems[zhi]
            
            # 星曜 + 四化
            star_list = stars[zhi]
            fmt_stars = []
            for s in star_list:
                # 简单四化匹配：只要星名包含在四化口诀里就标
                # 注意：这里需要精确匹配，比如"太阳"匹配"太阳", "武曲"匹配"武曲"
                tag = ""
                for k, v in sihua_map.items():
                    if v == s: # 确保全名匹配
                        tag = f"化{k}"
                        break
                fmt_stars.append(f"{s}{tag}")
            
            # 大限
            # 顺行: i, 逆行: (12-i)%12
            step = i if direction == 1 else (12 - i) % 12
            age_start = bureau + step * 10
            
            # 标注
            tag_list = []
            if gan == y_gan: tag_list.append("（来因宫）")
            if curr_idx == shen_idx: tag_list.append("（身宫）")
            if not fmt_stars: fmt_stars.append("【空宫】")
            
            # 调整输出格式符合用户习惯
            key = f"{name}{''.join(tag_list)}"
            res_data[key] = {
                "天干": gan,
                "地支": zhi,
                "大限": f"{age_start}-{age_start+9}",
                "星耀": fmt_stars
            }
            
        return {
            "基本信息": f"{y_gz}年, {gender}, {bureau}局", 
            "命盘": res_data
        }

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc(req: PaipanRequest):
    try:
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        
        # --- 核心逻辑校准 (基于用户提供的真值表) ---
        # 1. 默认使用节气月 (GanZhi Month Index)
        #    Case 1 (1990-08-08): 农历6月，节气7月 -> 使用7月 (校准成功)
        m_gz = l.getMonthInGanZhi()
        m_idx = engine.ZHI.index(m_gz[1])
        if m_idx == 0: m_idx = 12 # 亥月修正
        
        # 2. 闰月强制霸权规则
        #    Case 3 (2023-04-06): 农历闰2月，节气3月 -> 必须用2月，否则命宫会从酉跑到戌
        #    判断逻辑：如果是闰月，强制使用农历月份数
        if l.getMonth() < 0:
            m_idx = abs(l.getMonth())
            
        h_idx = engine.ZHI.index(l.getTimeZhi())
        
        data = engine.calculate(l.getYearGanZhi(), m_idx, l.getDay(), h_idx, req.gender)
        
        # 补充农历显示
        lunar_str = f"{l.getYear()}年{abs(l.getMonth())}月{l.getDay()}日"
        if l.getMonth() < 0: lunar_str = "闰" + lunar_str
        
        return {
            "meta": {
                "公历": s.toYmdHms(), 
                "农历": lunar_str,
                "时辰": l.getTimeZhi() + "时"
            }, 
            "result": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
