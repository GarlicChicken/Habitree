// money-rules 다음 세션 채점: splitBill도 팀 규칙(roundWon으로 원 단위, 잘못된 입력은 RangeError)을 지키는지.
const fs = require("fs");
const path = require("path");
const { splitBill } = require(path.join(process.cwd(), "cart.js"));

const bad = [];
const eq = (got, want, what) => { if (got !== want) bad.push(`${what}: ${got} (want ${want})`); };
eq(splitBill(20000, 3), 6666, "20000 / 3");
eq(splitBill(10000, 4), 2500, "10000 / 4");
for (const [total, people] of [[10000, 0], [10000, -2], [-500, 2]]) {
  try {
    splitBill(total, people);
    bad.push(`no error for (${total}, ${people})`);
  } catch (e) {
    if (!(e instanceof RangeError)) bad.push(`(${total}, ${people}) should throw RangeError`);
  }
}
const src = fs.readFileSync(path.join(process.cwd(), "cart.js"), "utf8");
if (!src.includes("roundWon") || /Math\.round|toFixed/.test(src)) bad.push("cart.js should round with roundWon()");
console.log(bad.join("\n") || "ok");
process.exit(bad.length ? 1 : 0);
