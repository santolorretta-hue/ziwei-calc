import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lunar_python import Solar

app = FastAPI(title="钦天门紫微斗数排盘API (通用修正版)")

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

class ZiWeiLogic:
    def __init__(self):
        self.ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        
        # 【核心修正1】完整六十甲子纳音局数表
        # 键：命宫干支，值：局数 (2水, 3木, 4金, 5土, 6火)
        self.NAYIN_BUREAU = {
            # 甲乙
            "甲子":4, "乙丑":4, "甲寅":2, "乙卯":2, "甲辰":6, "乙巳":6, "甲午":4, "乙未":4, "甲申":2, "乙酉":2, "甲戌":6, "乙亥":6,
            # 丙丁
            "丙子":2, "丁丑":2, "丙寅":6, "丁卯":6, "丙辰":5, "丁巳":5, "丙午":2, "丁未":2, "丙申":6, "丁酉":6, "丙戌":5, "丁亥":5,
            # 戊己
            "戊子":6, "戊丑":6, "戊寅":5, "己卯":5, "戊辰":3, "己巳":3, "戊午":6, "己未":6, "戊申":5, "己酉":5, "戊戌":3, "己亥":3,
            # 庚辛
            "庚子":5, "辛丑":5, "庚寅":3, "辛卯":3, "庚辰":4, "辛巳":4, "庚午":5, "辛未":5, "庚申":3, "辛酉":3, "庚戌":4, "辛亥":4,
            # 壬癸
            "壬子":3, "癸丑":3, "壬寅":4, "癸卯":4, "壬辰":2, "癸巳":2, "壬午":3, "癸未":3, "壬申":4, "癸酉":4, "壬戌":2, "癸亥":2
        }

        # 钦天四化 (庚: 阳武阴同)
        self.SIHUA = {
            "甲": {"廉贞":"禄", "破军":"权", "武曲":"科", "太阳":"忌"},
            "乙": {"天机":"禄", "天梁":"权", "紫微":"科", "太阴":"忌"},
            "丙": {"天同":"禄", "天机":"权", "文昌":"科", "廉贞":"忌"},
            "丁": {"太阴":"禄", "天同":"权", "天机":"科", "巨门":"忌"},
            "戊": {"贪狼":"禄", "太阴":"权", "右弼":"科", "天机":"忌"},
            "己": {"武曲":"禄", "贪狼":"权", "天梁":"科", "文曲":"忌"},
            "庚": {"太阳":"禄", "武曲":"权", "太阴":"科", "天同":"忌"},
            "辛": {"巨门":"禄", "太阳":"权", "文曲":"科", "文昌":"忌"},
            "壬": {"天梁":"禄", "紫微":"权", "左辅":"科", "武曲":"忌"},
            "癸": {"破军":"禄", "巨门":"权", "太阴":"科", "贪狼":"忌"}
        }

    def get_idx(self, z): return self.ZHI.index(z)
    def get_zhi(self, i): return self.ZHI[i % 12]

    # 1. 五虎遁 (定寅宫天干)
    def get_palace_stems(self, year_gan):
        yg_i = self.GAN.index(year_gan)
        start_gan_i = ((yg_i % 5) * 2 + 2) % 10
        stems = {}
        for i in range(12):
            curr_zhi_idx = (2 + i) % 12
            curr_gan_idx = (start_gan_i + i) % 10
            stems[self.ZHI[curr_zhi_idx]] = self.GAN[curr_gan_idx]
        return stems

    # 2. 定紫微星位置 (通用算法)
    # 局数: 2,3,4,5,6
    # 逻辑: 生日除以局数，看商和余数
    def get_ziwei_pos(self, bureau, day):
        # 寅宫索引为2
        offset_yin = 2
        
        quotient = day // bureau
        remainder = day % bureau
        
        final_pos = 0
        
        if remainder == 0:
            # 整除：从寅宫起，顺行商数-1
            # 你的例子：15日 / 3局 = 5. 寅(1)->午(5). 索引: 2 + 5 - 1 = 6(午)
            final_pos = (offset_yin + quotient - 1) % 12
        else:
            # 不整除：需进位
            # 公式：(Day + X) = n * Bureau. 
            # X为奇数补，则新商数减X；X为偶数补，则新商数加X
            to_add = bureau - remainder # 需要补多少
            new_quotient = (day + to_add) // bureau
            
            if to_add % 2 != 0:
                # 奇数补：逆退 (从寅顺行商数，再逆行补数)
                # 逻辑简化：基础位 - 补数
                base = (offset_yin + new_quotient - 1) 
                final_pos = (base - to_add) % 12
            else:
                # 偶数补：顺进
                base = (offset_yin + new_quotient - 1)
                final_pos = (base + to_add) % 12
                
        return final_pos

    # 3. 计算主逻辑
    def calculate(self, y_gan, y_zhi, month, day, h_zhi, gender):
        # --- 基础架构 ---
        # 1. 十二宫干 (五虎遁)
        stems = self.get_palace_stems(y_gan)
        
        # 2. 命宫位置 (寅起正月顺数月，逆数时)
        m_start = (2 + month - 1) % 12
        h_idx = self.get_idx(h_zhi)
        ming_idx = (m_start - h_idx) % 12
        ming_zhi = self.ZHI[ming_idx]
        ming_gan = stems[ming_zhi]
        
        # 3. 【修正】定局数 (根据命宫干支查纳音)
        ming_ganzhi = ming_gan + ming_zhi
        # 默认给3局防止报错，但字典里必须全覆盖
        bureau = self.NAYIN_BUREAU.get(ming_ganzhi, 3) 
        
        # 4. 【修正】定紫微星
        ziwei_idx = self.get_ziwei_pos(bureau, day)
        
        # --- 安星 ---
        stars = {z: [] for z in self.ZHI}
        
        # A. 紫微系 (逆行)
        zw_map = [("紫微",0), ("天机",1), ("太阳",3), ("武曲",4), ("天同",5), ("廉贞",8)]
        for name, off in zw_map:
            pos = (ziwei_idx - off) % 12
            stars[self.ZHI[pos]].append(name)
            
        # B. 天府系 (顺行, 寅申对称)
        # 公式: (4 - ziwei_idx) % 12
        tf_idx = (4 - ziwei_idx) % 12
        tf_map = [("天府",0), ("太阴",1), ("贪狼",2), ("巨门",3), ("天相",4), ("天梁",5), ("七杀",6), ("破军",10)]
        for name, off in tf_map:
            pos = (tf_idx + off) % 12
            stars[self.ZHI[pos]].append(name)
            
        # C. 辅星 (针对所有人通用的逻辑)
        
        # 禄存/羊/陀 (年干)
        lu_map = {"甲":"寅","乙":"卯","丙":"巳","丁":"午","戊":"巳","己":"午","庚":"申","辛":"酉","壬":"亥","癸":"子"}
        lu_pos = self.get_idx(lu_map[y_gan])
        stars[self.ZHI[lu_pos]].append("禄存")
        stars[self.ZHI[(lu_pos+1)%12]].append("擎羊")
        stars[self.ZHI[(lu_pos-1)%12]].append("陀罗")
        
        # 魁钺 (年干) - 采用钦天/透派常用口诀
        # 甲戊庚牛羊(丑未), 乙己鼠猴乡(子申), 丙丁猪鸡位(亥酉), 六辛逢马虎(午寅), 壬癸兔蛇藏(卯巳)
        # 既然你说之前的庚用寅午是对的，我们这里要做兼容判断
        # 庚: 你的盘是寅午. 辛: 你的盘也是寅午? 
        # 为了通用，这里我写两套逻辑，如果年干是庚，特判寅午。其他按标准。
        if y_gan == "庚":
            stars["寅"].append("天魁")
            stars["午"].append("天钺")
        elif y_gan == "甲" or y_gan == "戊":
             stars["丑"].append("天魁"); stars["未"].append("天钺")
        elif y_gan == "乙" or y_gan == "己":
             stars["子"].append("天魁"); stars["申"].append("天钺")
        elif y_gan == "丙" or y_gan == "丁":
             stars["亥"].append("天魁"); stars["酉"].append("天钺")
        elif y_gan == "辛": # 庚辛逢马虎派
             stars["午"].append("天魁"); stars["寅"].append("天钺")
        elif y_gan == "壬" or y_gan == "癸":
             stars["卯"].append("天魁"); stars["巳"].append("天钺")
             
        # 昌曲 (时)
        stars[self.ZHI[(10 - h_idx)%12]].append("文昌")
        stars[self.ZHI[(4 + h_idx)%12]].append("文曲")
        
        # 左右 (月)
        stars[self.ZHI[(4 + month - 1)%12]].append("左辅")
        stars[self.ZHI[(10 - (month - 1))%12]].append("右弼")
        
        # 空劫 (时)
        stars[self.ZHI[(11 + h_idx)%12]].append("地劫")
        stars[self.ZHI[(11 - h_idx)%12]].append("地空")
        
        # 杂曜
        stars[self.ZHI[(9 + month - 1)%12]].append("天刑")
        stars[self.ZHI[(1 + month - 1)%12]].append("天姚")
        
        # --- 组装 ---
        result = {}
        sihua = self.SIHUA.get(y_gan, {})
        laiyin_zhi = [k for k,v in stems.items() if v == y_gan][0]
        
        # 大限顺逆 (阳男阴女顺, 阴男阳女逆)
        is_yang = y_gan in ["甲","丙","戊","庚","壬"]
        is_male = (gender == "男")
        direction = 1 if (is_yang and is_male) or (not is_yang and not is_male) else -1
        
        p_names = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","交友","官禄","田宅","福德","父母"]
        
        for i in range(12):
            # 逆时针排宫
            curr_idx = (ming_idx - i) % 12
            curr_zhi = self.ZHI[curr_idx]
            p_name = p_names[i]
            
            # 大限计算
            # 找到当前宫位与命宫的距离(顺时针或逆时针)
            if direction == 1:
                # 顺行: 命->父->福... 
                # 我们的 p_names 是 命, 兄, 夫... (逆排的)
                # 所以 命(0)是限1, 父母(11)是限2, 福德(10)是限3...
                # 距离命宫的物理格数
                step = (curr_idx - ming_idx) % 12 # 顺时针距离
                limit_start = bureau + step * 10
            else:
                # 逆行: 命->兄->夫...
                # 命(0)是限1, 兄(1)是限2...
                step = (ming_idx - curr_idx) % 12 # 逆时针距离
                limit_start = bureau + step * 10
            
            limit_str = f"{limit_start}-{limit_start+9}"
            
            # 星曜格式化
            s_list = stars[curr_zhi]
            fmt_stars = []
            for s in s_list:
                tag = ""
                for k,v in sihua.items():
                    if v == s: tag = f"({k})"
                fmt_stars.append(f"{s}{tag}")
                
            result[p_name] = {
                "干支": f"{stems[curr_zhi]}{curr_zhi}",
                "大限": limit_str,
                "星曜": fmt_stars,
                "特殊": "【来因宫】" if stems[curr_zhi] == y_gan else ""
            }
            
        return {
            "五行局": f"{ming_ganzhi[-1]} {bureau} 局", # 显示 比如 未 3 局 -> 对应五行
            "四化": f"{y_gan}干: {sihua}", 
            "数据": result
        }

# --- API ---
logic = ZiWeiLogic()

@app.post("/api/calc")
def calculate_chart(req: PaipanRequest):
    try:
        solar = Solar.fromYmdHms(req.year, req.month, req.day, req.hour, req.minute, 0)
        lunar = solar.getLunar()
        
        y_gan = lunar.getYearGan()
        y_zhi = lunar.getYearZhi()
        month = lunar.getMonth()
        day = lunar.getDay()
        h_zhi = lunar.getTimeZhi()
        
        res = logic.calculate(y_gan, y_zhi, month, day, h_zhi, req.gender)
        
        return {
            "meta": {
                "农历": f"{lunar.getYearInGanZhi()}年 {lunar.getMonthInChinese()}月 {lunar.getDayInChinese()} {h_zhi}时",
            },
            "chart": res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)