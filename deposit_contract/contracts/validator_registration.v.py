MIN_DEPOSIT_AMOUNT: constant(uint256) = 1000000000  # Gwei
MAX_DEPOSIT_AMOUNT: constant(uint256) = 32000000000  # Gwei
CHAIN_START_FULL_DEPOSIT_THRESHOLD: constant(uint256) = 16384  # 2**14
DEPOSIT_TREE_DEPTH: constant(uint256) = 32
TWO_TO_POWER_OF_TREE_DEPTH: constant(uint256) = 4294967296  # 2**32
SECONDS_PER_DAY: constant(uint256) = 86400
MAX_64_BIT_VALUE: constant(uint256) = 18446744073709551615  # 2**64 - 1

Deposit: event({deposit_root: bytes32, data: bytes[528], merkle_tree_index: bytes[8], branch: bytes32[32]})
ChainStart: event({deposit_root: bytes32, time: bytes[8]})

zerohashes: bytes32[32]
branch: bytes32[32]
deposit_count: uint256
full_deposit_count: uint256
chainStarted: public(bool)

@public
def __init__():
    for i in range(31):
        self.zerohashes[i+1] = sha3(concat(self.zerohashes[i], self.zerohashes[i]))
        self.branch[i+1] = self.zerohashes[i+1]

@private
@constant
def to_bytes8(value: uint256) -> bytes[8]:
    return slice(convert(value, bytes32), start=24, len=8)
    
@public
@constant
def to_little_endian_64(value: uint256) -> bytes[8]:
    assert value <= MAX_64_BIT_VALUE

    big_endian_64: bytes[8] = self.to_bytes8(value)

    # array access for bytes[] not currently supported in vyper so
    # reversing bytes using bitwise uint256 manipulations
    x: uint256 = convert(big_endian_64, uint256)
    y: uint256 = 0
    for i in range(8):
        y = shift(y, 8)
        y = y + bitwise_and(x, 255)
        x = shift(x, -8)

    return self.to_bytes8(y)

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
    deposit_amount: uint256 = msg.value / as_wei_value(1, "gwei")
    
    assert msg.value >= deposit_amount
    assert msg.value <= deposit_amount

    index: uint256 = self.deposit_count
    deposit_timestamp: uint256 = as_unitless_number(block.timestamp)
    deposit_data: bytes[528] = concat(self.to_little_endian_64(deposit_amount), self.to_little_endian_64(deposit_timestamp), deposit_input)
    merkle_tree_index: bytes[8] = self.to_little_endian_64(index)

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
    new_deposit_root: bytes32 = self.get_deposit_root()
    log.Deposit(new_deposit_root, deposit_data, merkle_tree_index, self.branch)

    if deposit_amount == MAX_DEPOSIT_AMOUNT:
        self.full_deposit_count += 1
        if self.full_deposit_count == CHAIN_START_FULL_DEPOSIT_THRESHOLD:
            timestamp_day_boundary: uint256 = as_unitless_number(block.timestamp) - as_unitless_number(block.timestamp) % SECONDS_PER_DAY + SECONDS_PER_DAY
            chainstart_time: bytes[8] = self.to_little_endian_64(timestamp_day_boundary)
            log.ChainStart(new_deposit_root, chainstart_time)
            self.chainStarted = True
