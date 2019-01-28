MIN_DEPOSIT_AMOUNT: constant(uint256) = 1000000000  # Gwei
MAX_DEPOSIT_AMOUNT: constant(uint256) = 32000000000  # Gwei
GWEI_PER_ETH: constant(uint256) = 1000000000  # 10**9
CHAIN_START_FULL_DEPOSIT_THRESHOLD: constant(uint256) = 16384  # 2**14
DEPOSIT_CONTRACT_TREE_DEPTH: constant(uint256) = 32
TWO_TO_POWER_OF_TREE_DEPTH: constant(uint256) = 4294967296  # 2**32
SECONDS_PER_DAY: constant(uint256) = 86400

Deposit: event({previous_deposit_root: bytes32, data: bytes[528], merkle_tree_index: bytes[8], branch: bytes32[32]})
ChainStart: event({deposit_root: bytes32, time: bytes[8]})

zerohashes: bytes32[32]
branch: bytes32[32]
deposit_count: uint256
full_deposit_count: uint256

@public
def __init__():
    for i in range(31):
        self.zerohashes[i+1] = sha3(concat(self.zerohashes[i], self.zerohashes[i]))
        self.branch[i+1] = self.zerohashes[i+1]

@public
@constant
def get_deposit_root() -> bytes32:
    root:bytes32 = 0x0000000000000000000000000000000000000000000000000000000000000000
    size:uint256 = self.deposit_count
    for h in range(32):
        if size % 2 == 1:
            root = sha3(concat(self.branch[h], root))
        else:
            root = sha3(concat(root, self.zerohashes[h]))
        size /= 2
    return root

@payable
@public
def deposit(deposit_input: bytes[512]):
    assert msg.value >= as_wei_value(MIN_DEPOSIT_AMOUNT, "gwei")
    assert msg.value <= as_wei_value(MAX_DEPOSIT_AMOUNT, "gwei")

    index: uint256 = self.deposit_count
    deposit_amount: bytes[8] = slice(concat("", convert(msg.value / GWEI_PER_ETH, bytes32)), start=24, len=8)
    deposit_timestamp: bytes[8] = slice(concat("", convert(block.timestamp, bytes32)), start=24, len=8)
    deposit_data: bytes[528] = concat(deposit_amount, deposit_timestamp, deposit_input)
    merkle_tree_index: bytes[8] = slice(concat("", convert(index, bytes32)), start=24, len=8)

    # add deposit to merkle tree
    i: int128 = 0
    power_of_two: uint256 = 2
    for _ in range(32):
        if (index+1) % power_of_two != 0:
            break
        i += 1
        power_of_two *= 2
    value:bytes32 = sha3(deposit_data)
    for j in range(32):
        if j < i:
            value = sha3(concat(self.branch[j], value))
    self.branch[i] = value

    self.deposit_count += 1
    root: bytes32 = self.get_deposit_root()
    log.Deposit(root, deposit_data, merkle_tree_index, self.branch)

    if msg.value == as_wei_value(MAX_DEPOSIT_AMOUNT, "gwei"):
        self.full_deposit_count += 1
        if self.full_deposit_count == CHAIN_START_FULL_DEPOSIT_THRESHOLD:
            timestamp_day_boundary: uint256 = as_unitless_number(block.timestamp) - as_unitless_number(block.timestamp) % SECONDS_PER_DAY + SECONDS_PER_DAY
            chainstart_time: bytes[8] = slice(concat("", convert(timestamp_day_boundary, bytes32)), start=24, len=8)
            log.ChainStart(root, chainstart_time)
