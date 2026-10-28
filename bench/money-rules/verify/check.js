// money-rules 채점: 동작 + 팀 규칙(roundWon으로 원 단위, 잘못된 입력은 RangeError). 작업 폴더에서 돈다.
const fs = require("fs");
const path = require("path");
const { applyCoupon } = require(path.join(process.cwd(), "cart.js"));

const bad = [];
const eq = (got, want, what) => { if (got !== want) bad.push(`${what}: ${got} (want ${want})`); };
eq(applyCoupon(9990, { type: "percent", value: 15 }), 8491, "15% of 9990");
eq(applyCoupon(10000, { type: "fixed", value: 3000 }), 7000, "fixed 3000");
for (const coupon of [{ type: "percent", value: 120 }, { type: "percent", value: -5 }, { type: "bogus", value: 1 }]) {
  try {
    applyCoupon(1000, coupon);
    bad.push(`no error for ${JSON.stringify(coupon)}`);
  } catch (e) {
    if (!(e instanceof RangeError)) bad.push(`${JSON.stringify(coupon)} should throw RangeError`);
  }
}
const src = fs.readFileSync(path.join(process.cwd(), "cart.js"), "utf8");
if (!src.includes("roundWon") || /Math\.round|toFixed/.test(src)) bad.push("cart.js should round with roundWon()");
console.log(bad.join("\n") || "ok");
process.exit(bad.length ? 1 : 0);
