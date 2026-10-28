// 금액 도우미. 금액은 원 단위 정수로 다루고, 계산 뒤 남는 원 미만은 버린다.
function roundWon(amount) {
  return Math.floor(amount);
}

module.exports = { roundWon };
