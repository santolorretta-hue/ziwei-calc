import uvicorn
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="紫微斗数API (钦天专家诊断版)")

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
        
        # 纳音数 -> 五行局名
        self.BUREAU_MAP = {2:"水二局", 3:"木三局", 4:"金四局", 5:"土五局", 6:"火六局"}
        
        self.NAYIN = {
            "甲子":4,"乙丑":4,"丙寅":6,"丁卯":6,"戊辰":5,"己巳":5,"庚午":5,"辛未":5,"壬申":4,"癸酉":4,
            "甲戌":6,"乙亥":6,"丙子":2,"丁丑":2,"戊寅":5,"己卯":5,"庚辰":4,"辛巳":4,"壬午":5,"癸未":3,
            "甲申":2,"乙酉":2,"丙戌":5,"丁亥":5,"戊子":6,"己丑":6,"庚寅":5,"辛卯":5,"壬辰":2,"癸巳":2,
            "甲午":4,"乙未":4,"丙申":6,"丁酉":6,"戊戌":5,"己亥":5,"庚子":5,"辛丑":5,"壬寅":4,"癸卯":4,
            "甲辰":6,"乙巳":6,"丙午":2,"丁未":2,"戊申":5,"己酉":5,"庚戌":4,"辛亥":4,"壬子":5,"癸丑":5,
            "甲寅":2,"乙卯":2,"丙辰":5,"丁巳":5,"戊午":6,"己未":6,"庚申":5,"辛酉":5,"壬戌":2,"癸亥":2
        }
        
        # 四化口诀 (全名匹配)
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
        
        ky = {"甲":["丑","未"], "乙":["子","申"], "丙":["亥","酉"], "丁":["亥","酉"],
              "戊":["丑","未"], "己":["子","申"], "庚":["丑","未"], "辛":["午","寅"],
              "壬":["卯","巳"], "癸":["卯","巳"]}.get(y_gan, [])
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

    # [新增] 检查自化逻辑
    def check_zihua(self, palace_gan, star_list):
        # 获取该宫干对应的四化规则
        rules = self.SIHUA.get(palace_gan, {})
        zihua_results = []
        for type_key, star_name in rules.items():
            # 检查该星是否在当前宫位内
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
        
        # 核心判定变量
        laiyin_palace = ""
        laiyin_type = ""
        laiyin_desc = ""
        laiyin_index = -1 # 记录来因宫是第几个宫 (0-11)
        self_reliant_list = ["命宫", "疾厄", "财帛", "官禄", "田宅", "福德"]
        
        res_data = {}
        report_lines = []
        diagnosis_lines = [] # 专家诊断报告
        
        for i, name in enumerate(p_names):
            curr_idx = (ming_idx - i) % 12
            zhi = self.ZHI[curr_idx]
            gan = stems[zhi]
            
            star_list = stars[zhi]
            
            # 1. 检查自化
            zihua_res = self.check_zihua(gan, star_list)
            zihua_str = ""
            if zihua_res:
                zihua_str = "【" + "、".join(zihua_res) + "】"
                # 加入诊断报告
                if "自化忌" in zihua_res:
                    diagnosis_lines.append(f"⚠️ {name}（{gan}干）出现{zihua_str}：注意破耗、流失、不按常理出牌的变数。")
                elif "自化禄" in zihua_res:
                    diagnosis_lines.append(f"ℹ️ {name}（{gan}干）出现{zihua_str}：缘分来去匆匆，易得易失。")
            
            # 2. 标记生年四化
            fmt_stars = []
            for s in star_list:
                tag = ""
                for type_key, star_name in sihua_rules.items():
                    if star_name == s:
                        tag = f"（化{type_key}）"
                        break
                fmt_stars.append(f"{s}{tag}")
            
            # 3. 大限
            if direction == -1: 
                limit_rank = i 
            else: 
                limit_rank = (12 - i) % 12
            age_start = bureau_num + limit_rank * 10
            limit_str = f"{age_start}-{age_start+9}岁"
            
            tag_list = []
            special_title = ""
            
            # 4. 来因宫判定
            if gan == y_gan: 
                tag_list.append("（来因宫）")
                special_title += "（同时也是来因宫）"
                laiyin_palace = name
                laiyin_index = i # 记录索引
                if name in self_reliant_list:
                    laiyin_type = "自立格"
                    laiyin_desc = "祸福自担，成功靠自己，因果不假外求。"
                else:
                    laiyin_type = "他立格"
                    laiyin_desc = "这一生的成败、缘分、债务，都与“他人”或“外部环境”深度捆绑。"

            if curr_idx == shen_idx: 
                tag_list.append("（身宫）")
                special_title += "（同时也是身宫）"
            
            # 组装数据
            res_data[name] = {
                "天干": gan,
                "地支": zhi,
                "干支": f"{gan}{zhi}", 
                "星曜": fmt_stars if fmt_stars else ["【空宫】"],
                "大限": limit_str,
                "标注": " ".join(tag_list),
                "自化": zihua_res
            }
            
            stars_str = "，".join(fmt_stars) if fmt_stars else "空宫"
            line = f"{name}{special_title}（大限{limit_str}）天干：{gan}，地支：{zhi}，星耀：{stars_str} {zihua_str}"
            report_lines.append(line)
        
        # --- 5. 河图数位联动诊断 (1-6, 4-9, 5-10) ---
        hetu_diag = []
        # 来因宫是启动点，看它引动了哪条线
        # p_names 顺序: 命0 兄1 夫2 子3 财4 疾5 迁6 友7 官8 田9 福10 父11
        if laiyin_index != -1:
            # 河图对应关系 (索引差值)
            hetu_pairs = {
                0: (5, "命疾线 (1-6)"), 5: (0, "命疾线 (1-6)"),
                3: (8, "子官线 (4-9)"), 8: (3, "子官线 (4-9)"),
                4: (9, "财田线 (5-10)"), 9: (4, "财田线 (5-10)")
            }
            
            if laiyin_index in hetu_pairs:
                target_idx, line_name = hetu_pairs[laiyin_index]
                target_name = p_names[target_idx]
                hetu_diag.append(f"🔗 来因宫在【{laiyin_palace}】，引动【{line_name}】能量：")
                hetu_diag.append(f"   需重点关注【{laiyin_palace}】与【{target_name}】的体用关系。")
                if line_name == "子官线 (4-9)":
                    hetu_diag.append(f"   💡 提示：合伙/桃花/下属（子女）直接决定事业格局（官禄）。")
                elif line_name == "财田线 (5-10)":
                    hetu_diag.append(f"   💡 提示：现金流（财帛）与资产库（田宅）的转化是人生关键。")
        
        # 整合诊断报告
        final_diagnosis = []
        if hetu_diag:
            final_diagnosis.append("【河图数位联动】")
            final_diagnosis.extend(hetu_diag)
            final_diagnosis.append("")
        
        if diagnosis_lines:
            final_diagnosis.append("【全盘自化风险扫描】")
            final_diagnosis.extend(diagnosis_lines)
        
        return {
            "局数": bureau_name,
            "性别描述": full_gender,
            "核心": {
                "命宫": self.ZHI[ming_idx], 
                "来因": y_gan,
                "来因宫位": laiyin_palace,
                "定格": laiyin_type,
                "格论": laiyin_desc
            },
            "数据": res_data,
            "文本报告": report_lines,
            "专家诊断": final_diagnosis
        }

engine = ZiWeiEngine()

@app.post("/api/calc")
def calc(req: PaipanRequest):
    try:
        s = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        l = s.getLunar()
        
        # 1. 农历定月 + 闰月分界
        raw_month = l.getMonth() 
        day = l.getDay()
        
        if raw_month < 0: 
            m_idx = abs(raw_month)
            if day > 15: m_idx += 1
        else:
            m_idx = raw_month
        if m_idx > 12: m_idx = 1
        
        # 2. 农历年干
        y_gz = l.getYearInGanZhi()
        y_gan = y_gz[0]
        y_zhi = y_gz[1]
        
        h_idx = engine.ZHI.index(l.getTimeZhi())
        
        zodiac = engine.ZODIAC.get(y_zhi)
        current_year = datetime.datetime.now().year
        age = current_year - req.year + 1
        
        data = engine.calculate(y_gan, y_zhi, m_idx, day, h_idx, req.gender)
        
        # 组装文本
        header = f"{data['局数']}，{data['性别描述']}，干支：{y_gz}年，年龄：{age}岁，属相：{zodiac}，阴历（农历）：{l.getYear()}.{abs(raw_month)}.{day}，阳历（公历）：{req.year}.{req.month}.{req.day}，时辰：{l.getTimeZhi()}时"
        
        # 核心定格
        core_info = f"🟦 格局判定：{data['核心']['来因宫位']}来因 -> 【{data['核心']['定格']}】\n   {data['核心']['格论']}"
        
        full_text_output = header + "\n\n" + core_info + "\n\n" + "\n\n".join(data["文本报告"])
        
        sihua_info = engine.SIHUA.get(y_gan, {})
        sihua_desc = f"🔴 {y_gan}干生年四化：{sihua_info.get('禄')}禄，{sihua_info.get('权')}权，{sihua_info.get('科')}科，{sihua_info.get('忌')}忌"
        full_text_output += f"\n\n{sihua_desc}"
        
        # 加上专家诊断
        if data["专家诊断"]:
             full_text_output += "\n\n──────────────\n🔎 钦天专家诊断：\n" + "\n".join(data["专家诊断"])

        response = {
            "meta": {
                "公历": s.toYmdHms(),
                "农历": f"{l.getYear()}年{l.getMonth()}月{l.getDay()}日",
                "四化重点": sihua_desc
            },
            "formatted_output": full_text_output,
            "result": data["数据"]
        }
        return response

    except Exception as e:
        return {
            "error": True, 
            "message": str(e),
            "formatted_output": f"排盘计算异常：{str(e)}",
            "result": {}
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
