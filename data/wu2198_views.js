/**
 * wu2198 投资观点追踪
 * 分类: 美股 | 港股 | A股点位 | A股板块 | 黄金 | 其他投资观点
 * 
 * ⚠️ source_url: 微博单条链接格式为 https://weibo.com/1216826604/<post_id>
 *    可从微博右上角「分享→复制链接」获取，或 RSSHub 自动化提取。
 *    当前未核实原文的条目使用主页地址占位。
 */
/**
 * 数据结构说明:
 *   date/time/category/tags/content/source_url/verified — 基础字段
 *   summary  — 一句话摘要（可选，用于总结区）
 *   levels   — 点位快照（仅 A股点位/港股/美股 有指数点位时填写）
 *      { close, support[], resistance[], note }
 */
var WU2198_VIEWS = [
  {
    date: "2026-06-25",
    time: "09:15",
    category: "A股点位",
    tags: ["大盘", "阻力位"],
    content: "今天注意看4250附近的压力，短线阻力比较大，操作上波段为主。",
    summary: "大盘短线关注 4250 阻力",
    levels: {
      resistance: [4250],
      support: [],
      close: null,
      note: "短线阻力较大，波段操作为主"
    },
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-25",
    time: "10:30",
    category: "黄金",
    tags: ["伦敦金", "调整"],
    content: "目前伦敦金试了3964美元，整体上看向3500美元调整的趋势和方向不变。自5598.75美元的下跌，第一步起码在4000美元（曾到过4098美元），然后才是3500美元。……明白666",
    summary: "伦敦金现报 3964，调整目标看向 3500 美元",
    levels: {
      close: 3964,
      support: [3500],
      resistance: [4000, 4098],
      note: "自 5598.75 高点下跌趋势不变"
    },
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-24",
    time: "21:40",
    category: "美股",
    tags: ["科技股", "纳斯达克"],
    content: "美股开盘后，老登股领涨，科技股分化。目前道指上涨55点、纳指跌163点。",
    summary: "美股开盘分化：道指 +55点，纳指 -163点",
    source_url: "https://weibo.com/1216826604/bsjkpzoee",
    verified: true
  },
  {
    date: "2026-06-24",
    time: "14:30",
    category: "A股板块",
    tags: ["AI硬件", "CPO", "泡沫风险"],
    content: "AI科技和光模块泡沫太大了，最近几天一直在说风险，但很多人不以为然。回想当年白酒抱团瓦解前的景象，何其相似。",
    summary: "AI硬件 / CPO 泡沫风险警示，类比白酒抱团瓦解",
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-23",
    time: "15:05",
    category: "A股点位",
    tags: ["收盘", "震荡"],
    content: "今天大盘收在4186点，缩量震荡。短线支撑看4150，破了的话下一支撑在4080附近。",
    summary: "收盘 4186 缩量震荡，短线支撑 4150 → 4080",
    levels: {
      close: 4186,
      support: [4150, 4080],
      resistance: [],
      note: "缩量震荡，跌破 4150 则看 4080"
    },
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-22",
    time: "11:20",
    category: "港股",
    tags: ["恒生指数", "南向资金"],
    content: "港股今天恒指低开高走，南向资金持续流入。科技股腾讯、美团反弹力度不错，但银行股拖累指数。",
    summary: "港股低开高走，南向持续流入；腾讯美团反弹，银行拖累",
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-20",
    time: "22:15",
    category: "美股",
    tags: ["科技股", "英伟达"],
    content: "英伟达今晚又新高了，但AI概念股内部已经开始分化。有些蹭概念的个股要注意风险，真AI和假AI的区别会越来越大。",
    summary: "英伟达新高，但 AI 概念股分化，警惕蹭概念个股",
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-18",
    time: "10:40",
    category: "A股板块",
    tags: ["半导体", "芯片", "国产替代"],
    content: "半导体板块今天走强，国产替代逻辑依然成立。但要注意个股分化，不要追高。",
    summary: "半导体走强，国产替代逻辑成立，不追高",
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-15",
    time: "16:00",
    category: "其他投资观点",
    tags: ["投资理念", "风险管理"],
    content: "投资股市只适合利用自己的空闲资金，而且一定要量力而为，风险永远放在第一位。不要举债，不要用杠杆，理性+价值+组合式投资相结合，将风险控制在自己能承受的范围之内。",
    summary: "核心理念：闲钱投资、不用杠杆、理性+价值+组合",
    source_url: "https://weibo.com/1216826604/8B4tC3",
    verified: true
  },
  {
    date: "2026-06-12",
    time: "09:30",
    category: "A股点位",
    tags: ["年度预测", "区间"],
    content: "大盘指数2026年最低看2856点，实际操作点2986点；最高看4250点，实际操作点3986点。在这个区间内波段操作即可。",
    summary: "2026 年度区间：最低 2856→2986，最高 3986→4250",
    levels: {
      close: null,
      support: [2856, 2986],
      resistance: [3986, 4250],
      note: "年度大区间波段操作"
    },
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-10",
    time: "21:00",
    category: "美股",
    tags: ["SpaceX", "IPO"],
    content: "马斯克麾下的SpaceX已确定首次公开募股(IPO)发行价为每股135美元，拟募资750亿美元，公司估值约1.77万亿美元。",
    summary: "SpaceX IPO：发行价 $135，估值 1.77 万亿美元",
    source_url: "https://weibo.com/1216826604/bsjkpzoee",
    verified: true
  },
  {
    date: "2026-06-05",
    time: "15:20",
    category: "A股板块",
    tags: ["CPO", "光模块", "AI硬件"],
    content: "从去年6月卖出并看空CPO到现在刚好一年。这一年里光模块里的10-20倍股如过江之鲫。但我依然认为这个位置风险远大于机会。",
    summary: "看空 CPO 一周年复盘：10-20倍股频出但风险＞机会",
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-06-01",
    time: "20:30",
    category: "港股",
    tags: ["恒生科技", "估值"],
    content: "港股恒生科技指数经历一轮调整后估值回到合理区间。中概股的基本面在改善，但流动性仍是制约因素。",
    summary: "恒生科技估值回合理区间，基本面改善但流动性制约",
    source_url: "https://weibo.com/1216826604/",
    verified: false
  },
  {
    date: "2026-03-23",
    time: "14:46",
    category: "黄金",
    tags: ["伦敦金", "下跌目标"],
    content: "伦敦金自5598.75美元的下跌，第一步起码在4000美元（曾到过4098美元）。然后才是3500美元......... 按目前看调整的趋势和方向不变…………明白666",
    summary: "伦敦金从高点 5598.75 回调，第一目标 4000 → 最终 3500",
    levels: {
      close: null,
      support: [3500],
      resistance: [4000, 4098, 5598.75],
      note: "自历史高点 5598.75 下跌趋势"
    },
    source_url: "https://weibo.com/1216826604/",
    verified: false
  }
];

/** 分类颜色映射 */
var WU2198_CATEGORY_COLORS = {
  "美股":    { bg: "#e3f2fd", border: "#1976d2", text: "#1565c0" },
  "港股":    { bg: "#fce4ec", border: "#c62828", text: "#b71c1c" },
  "A股点位": { bg: "#fff3e0", border: "#e65100", text: "#bf360c" },
  "A股板块": { bg: "#e8f5e9", border: "#2e7d32", text: "#1b5e20" },
  "黄金":    { bg: "#fff8e1", border: "#f9a825", text: "#e65100" },
  "其他投资观点": { bg: "#f3e5f5", border: "#6a1b9a", text: "#4a148c" }
};

/** 分类图标 */
var WU2198_CATEGORY_ICONS = {
  "美股": "🇺🇸",
  "港股": "🇭🇰",
  "A股点位": "📈",
  "A股板块": "🏭",
  "黄金": "🥇",
  "其他投资观点": "💡"
};
