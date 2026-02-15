import uvicorn
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="紫微斗数API (全功能专家诊断版)")

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
        self.ZODIAC = {"子":"鼠", "丑":"牛", "寅":"虎", "卯":"兔", "辰":"龙", "巳":"蛇", "午":"马", "未":"羊", "申":"猴", "酉":"鸡", "戌":"狗", "亥":"猪"}
        self.BUREAU_MAP = {2:"水二局", 3:"木三局", 4:"金四局", 5:"土五局", 6:"火六局"}
        self.NAYIN = {
            "甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
            "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
            "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
            "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
            "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
            "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2
        }
        self.SIHUA = {
            "甲": {"禄":"廉贞", "权":"破军", "科":"武曲", "忌":"太阳"},
            "乙": {"禄":"天机", "权":"天梁", "科":"紫微", "忌":"太阴"},
            "丙": {"禄":"天同", "权":"天机", "科":"文昌", "忌":"廉贞"},
            "丁": {"禄":"太阴", "权":"天同", "科":"天机", "忌":"巨门"},
            "戊": {"禄":"贪狼", "权":"太阴", "科":"右弼", "忌":"天机"},
            "己": {"禄":"武曲", "权":"贪狼", "科":"天梁", "忌":"文曲"},
            "庚": {"禄":"太阳", "权":"武曲", "科":"太阴", "忌":"天同"},
            "辛": {"禄":"巨门", "权":"太阳", "科":"文曲", "忌":"文昌"},
            "壬": {"禄":"天梁", "权":"紫微", "科":"左辅", "忌":"武曲"},
            "癸": {"禄":"破军", "权":"巨门", "科":"太阴", "忌":"贪狼"}
        }

    def get_ziwei_idx(self, bureau, day):
        for x in range(bureau):
            if (day + x) % bureau == 0:
                q = (day + x) // bureau
                base = (2 + q - 1) % 12
                return (base - x) % 12 if x % 2 != 0 else (base + x) % 12
        return 2

    def get_aux_stars(self, month_idx, h_idx, y_zhi, y_gan):
        stars = {z: [] for z in self.ZHI}
        stars[self.ZHI[(10 - h_idx) % 12]].append("文昌")
        stars[self.ZHI[(4 + h_idx) % 12]].append("文曲")
        stars[self.ZHI[(4 + month_idx - 1) % 12]].append("左辅")
        stars[self.ZHI[(10 - (month_idx - 1)) % 12]].append("右弼")
        ky = {"甲":["丑","未"], "乙":["子","申"], "丙":["亥","酉"], "丁":["亥","酉"], "戊":["丑","未"], "己":["子","申"], "庚":["丑","未"], "辛":["午","寅"], "壬":["卯","巳"], "癸":["卯","巳"]}.get(y_gan, [])
        if ky: stars[ky[0]].append("天魁"); stars[ky[1]].append("天钺")
        lu_map = {"甲":"寅","乙":"卯","丙":"巳","丁":"午","戊":"巳","己":"午","庚":"申","辛":"酉","壬":"亥","癸":"子"}
        if y_gan in lu_map:
            l_idx = self.ZHI.index(lu_map[y_gan])
            stars[self.ZHI[l_idx]].append("禄存")
            stars[self.ZHI[(l_idx+1)%12]].append("擎羊")
            stars[self.ZHI[(l_idx-1)%12]].append("陀罗")
        if y_zhi in "申子辰": start_h, start_l = 2, 10
        elif y_zhi in "寅午戌": start_h, start_l = 1, 3
        elif y_zhi in "亥卯未": start_h, start_l = 9, 10
        else: start_h, start_l = 3, 10
        stars[self.ZHI[(start_h + h_idx) % 12]].append("火星")
        stars[self.ZHI[(start_l + h_idx) % 12]].append("铃星")
        stars[self.ZHI[(11 + h_idx) % 12]].append("地劫")
        stars[self.ZHI[(11 - h_idx) % 12]].append("地空")
        stars[self.ZHI[(9 + month_idx - 1) % 12]].append("天刑")
        stars[self.ZHI[(1 + month_idx - 1) % 12]].append("天姚")
        y_idx = self.ZHI.index(y_zhi)
        luan_idx = (3 - y_idx) % 12
        stars[self.ZHI[luan_idx]].append("红鸾")
        stars[self.ZHI[(luan_idx + 6) % 12]].append("天喜")
        return stars

    def check_zihua(self, palace_gan, star_list):
        rules = self.SIHUA.get(palace_gan, {})
        zihua_results = []
        for type_key, star_name in rules.items():
            if star_name in star_list:
                zihua_results.append(f"自化{type_key}")
        return zihua_results

    def calculate(self, y_gan, y_zhi, m_idx, day, h_idx, gender):
        ming_idx = (2 + (m_idx - 1) - h_idx) % 12
        shen_idx = (2 + (m_idx - 1) + h_idx) % 12
        start_gan_idx = ((self.GAN.index(y_gan) % 5) * 2 + 2) % 10
        stems = {self.ZHI[(2+i)%12]: self.GAN[(start_gan_idx+i)%10] for i in range(12)}
        ming_gz = stems[self.ZHI[ming_idx]] + self.ZHI[ming_idx]
        bureau_num = self.NAYIN.get(ming_gz, 3)
        bureau_name = self.BUREAU_MAP.get(bureau_num, f"{bureau_num}局")
        zw_idx = self.get_ziwei_idx(bureau_num, day)
        tf_idx = (4 - zw_idx) % 12
        stars = {z: [] for z in self.ZHI}
        for n, o in [("紫微",0),("天机",1),("太阳",3),("武曲",4),("天同",5),("廉贞",8)]:
            stars[self.ZHI[(zw_idx-o)%12]].append(n)
        for n, o in [("天府",0),("太阴",1),("贪狼",2),("巨门",3),("天相",4),("天梁",5),("七杀",6),("破军",10)]:
            stars[self.ZHI[(tf_idx+o)%12]].append(n)
        aux_stars = self.get_aux_stars(m_idx, h_idx, y_zhi, y_gan)
        for z, slist in aux_stars.items(): stars[z].extend(slist)
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        is_yang_year = y_gan in "甲丙戊庚壬"
        direction = 1 if (is_yang_year and gender == "男") or (not is_yang_year and gender == "女") else -1
        yin_yang_gender = "阳" if is_yang_year else "阴"
        full_gender = f"{yin_yang_gender}{gender}"
        sihua_rules = self.SIHUA.get(y_gan, {})
        laiyin_palace, laiyin_type, laiyin_desc, laiyin_index = "", "", "", -1
        self_reliant_list = ["命宫", "疾厄", "财帛", "官禄", "田宅", "福德"]
        res_data, report_lines, diagnosis_lines = {}, [], []
        for i, name in enumerate(p_names):
            curr_idx = (ming_idx - i) % 12
            zhi = self.ZHI[curr_idx]
            gan = stems[zhi]
            star_list = stars[zhi]
            zihua_res = self.check_zihua(gan, star_list)
            zihua_str = "【" + "、".join(zihua_res) + "】" if zihua_res else ""
            if "自化忌" in zihua_res: diagnosis_lines.append(f"⚠️ {name}（{gan}干）出现{zihua_str}：注意破耗。")
            fmt_stars = []
            for s in star_list:
                tag = ""
                for type_key, star_name in sihua_rules.items():
                    if star_name == s: tag = f"（化{type_key}）"; break
                fmt_stars.append(f"{s}{tag}")
            limit_rank = i if direction == -1 else (12 - i) % 12
            age_start = bureau_num + limit_rank * 10
            limit_str = f"{age_start}-{age_start+9}岁"
            tag_list, special_title = [], ""
            if gan == y_gan:
                tag_list.append("（来因宫）"); special_title += "（同时也是来因宫）"
                laiyin_palace, laiyin_index = name, i
                if name in self_reliant_list: laiyin_type, laiyin_desc = "自立格", "祸福自担，成功靠自己。"
                else: laiyin_type, laiyin_desc = "他立格", "成败与外部环境捆绑。"
            if curr_idx == shen_idx: tag_list.append("（身宫）"); special_title += "（同时也是身宫）"
            res_data[name] = {"天干": gan, "地支": zhi, "星曜": fmt_stars if fmt_stars else ["【空宫】"], "自化": zihua_res}
            report_lines.append(f"{name}{special_title}（大限{limit_str}）星耀：{'，'.join(fmt_stars) if fmt_stars else '空宫'} {zihua_str}")
        
        final_diagnosis = ["【河图数位联动】"]
        if laiyin_index != -1:
            target_idx = (laiyin_index + 5) % 12
            final_diagnosis.append(f"🔗 来因宫在【{laiyin_palace}】，引动【{p_names[laiyin_index]}-{p_names[target_idx]}】能量。")
        
        return {
            "局数": bureau_name, "性别描述": full_gender,
            "核心": {"命宫": self.ZHI[ming_idx], "来因": y_gan, "来因宫位": laiyin_palace, "定格": laiyin_type, "格论": laiyin_desc},
            "数据": res_data, "文本报告": report_lines, "专家诊断": final_diagnosis
        }

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc(req: PaipanRequest):
    try:
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        raw_month, day = l.getMonth(), l.getDay()
        m_idx = abs(raw_month) + (1 if raw_month < 0 and day > 15 else 0)
        if m_idx > 12: m_idx = 1
        y_gz = l.getYearInGanZhi()
        data = engine.calculate(y_gz[0], y_gz[1], m_idx, day, engine.ZHI.index(l.getTimeZhi()), req.gender)
        return {
            "meta": {"公历": s.toYmdHms(), "农历": f"{l.getYear()}年{l.getMonth()}月{l.getDay()}日"},
            "formatted_output": "\n".join(data["文本报告"]),
            "result": data  # 确保返回完整的 data 对象
        }
    except Exception as e:
        return {"error": True, "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)