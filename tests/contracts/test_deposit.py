from random import (
    randint,
)

import pytest

from eth_hash.auto import (
    keccak as hash,
)
import eth_utils
from tests.contracts.conftest import (
    DEPOSIT_CONTRACT_TREE_DEPTH,
    MAX_DEPOSIT_AMOUNT,
    MIN_DEPOSIT_AMOUNT,
)


def compute_merkle_root(leaf_nodes):
    assert len(leaf_nodes) >= 1
    empty_node = b'\x00' * 32
    child_nodes = leaf_nodes[:]
    for i in range(DEPOSIT_CONTRACT_TREE_DEPTH):
        parent_nodes = []
        if len(child_nodes) % 2 == 1:
            child_nodes.append(empty_node)
        for j in range(0, len(child_nodes), 2):
            parent_nodes.append(hash(child_nodes[j] + child_nodes[j + 1]))
        child_nodes = parent_nodes
        empty_node = hash(empty_node + empty_node)
    return child_nodes[0]


@pytest.mark.parametrize(
    'value,success',
    [
        (0, True),
        (10, True),
        (55555, True),
        (2**64 - 1, True),
        (2**64, False),
    ]
)
def test_to_little_endian_64(registration_contract, value, success, assert_tx_failed):
    call = registration_contract.functions.to_little_endian_64(value)

    if success:
        little_endian_64 = call.call()
        assert little_endian_64 == (value).to_bytes(8, 'little')
    else:
        assert_tx_failed(
            lambda: call.call()
        )


@pytest.mark.parametrize(
    'success,deposit_amount',
    [
        (True, MAX_DEPOSIT_AMOUNT),
        (True, MIN_DEPOSIT_AMOUNT),
        (False, MIN_DEPOSIT_AMOUNT - 1),
        (False, MAX_DEPOSIT_AMOUNT + 1)
    ]
)
def test_deposit_amount(registration_contract, w3, success, deposit_amount, assert_tx_failed):

    call = registration_contract.functions.deposit(b'\x10' * 512)
    if success:
        assert call.transact({"value": deposit_amount * eth_utils.denoms.gwei})
    else:
        assert_tx_failed(
            lambda: call.transact({"value": deposit_amount * eth_utils.denoms.gwei})
        )


def test_deposit_log(registration_contract, a0, w3):
    log_filter = registration_contract.events.Deposit.createFilter(
        fromBlock='latest',
    )

    deposit_amount = [randint(MIN_DEPOSIT_AMOUNT, MAX_DEPOSIT_AMOUNT) for _ in range(3)]
    for i in range(3):
        deposit_input = (i + 1).to_bytes(1, 'little') * 512
        registration_contract.functions.deposit(
            deposit_input,
        ).transact({"value": deposit_amount[i] * eth_utils.denoms.gwei})

        logs = log_filter.get_new_entries()
        assert len(logs) == 1
        log = logs[0]['args']

        amount_bytes8 = deposit_amount[i].to_bytes(8, 'little')
        timestamp_bytes8 = int(
            w3.eth.getBlock(w3.eth.blockNumber)['timestamp']
        ).to_bytes(8, 'little')
        assert log['data'] == amount_bytes8 + timestamp_bytes8 + deposit_input
        assert log['merkle_tree_index'] == i.to_bytes(8, 'little')


def test_deposit_tree(registration_contract, w3, assert_tx_failed):
    log_filter = registration_contract.events.Deposit.createFilter(
        fromBlock='latest',
    )

    deposit_amount = [randint(MIN_DEPOSIT_AMOUNT, MAX_DEPOSIT_AMOUNT) for _ in range(10)]
    leaf_nodes = []
    for i in range(0, 10):
        deposit_input = (i + 1).to_bytes(1, 'little') * 512
        tx_hash = registration_contract.functions.deposit(
            deposit_input,
        ).transact({"value": deposit_amount[i] * eth_utils.denoms.gwei})
        receipt = w3.eth.getTransactionReceipt(tx_hash)
        print("deposit transaction consumes %d gas" % receipt['gasUsed'])

        logs = log_filter.get_new_entries()
        assert len(logs) == 1
        log = logs[0]['args']

        timestamp_bytes8 = int(
            w3.eth.getBlock(w3.eth.blockNumber)['timestamp']
        ).to_bytes(8, 'little')
        amount_bytes8 = deposit_amount[i].to_bytes(8, 'little')
        data = amount_bytes8 + timestamp_bytes8 + deposit_input
        assert log["data"] == data
        assert log["merkle_tree_index"] == i.to_bytes(8, 'little')
        leaf_nodes.append(hash(data))
        root = compute_merkle_root(leaf_nodes)
        assert root == registration_contract.functions.get_deposit_root().call()


def test_chain_start(modified_registration_contract, w3, assert_tx_failed):
    t = getattr(modified_registration_contract, 'chain_start_full_deposit_threshold')
    # CHAIN_START_FULL_DEPOSIT_THRESHOLD is set to t
    min_deposit_amount = MIN_DEPOSIT_AMOUNT * eth_utils.denoms.gwei  # in wei
    max_deposit_amount = MAX_DEPOSIT_AMOUNT * eth_utils.denoms.gwei
    log_filter = modified_registration_contract.events.Eth2Genesis.createFilter(
        fromBlock='latest',
    )

    index_not_full_deposit = randint(0, t - 1)
    for i in range(t):
        if i == index_not_full_deposit:
            # Deposit with value below MAX_DEPOSIT_AMOUNT
            deposit_input = b'\x01' * 512
            modified_registration_contract.functions.deposit(
                deposit_input,
            ).transact({"value": min_deposit_amount})
            logs = log_filter.get_new_entries()
            # Eth2Genesis event should not be triggered
            assert len(logs) == 0
        else:
            # Deposit with value MAX_DEPOSIT_AMOUNT
            deposit_input = i.to_bytes(1, 'little') * 512
            modified_registration_contract.functions.deposit(
                deposit_input,
            ).transact({"value": max_deposit_amount})
            logs = log_filter.get_new_entries()
            # Eth2Genesis event should not be triggered
            assert len(logs) == 0

    # Make 1 more deposit with value MAX_DEPOSIT_AMOUNT to trigger Eth2Genesis event
    deposit_input = b'\x06' * 512
    modified_registration_contract.functions.deposit(
        deposit_input,
    ).transact({"value": max_deposit_amount})
    logs = log_filter.get_new_entries()
    assert len(logs) == 1
    timestamp = int(w3.eth.getBlock(w3.eth.blockNumber)['timestamp'])
    timestamp_day_boundary = timestamp + (86400 - timestamp % 86400) + 86400
    log = logs[0]['args']
    assert log['deposit_root'] == modified_registration_contract.functions.get_deposit_root().call()
    assert int.from_bytes(log['time'], byteorder='little') == timestamp_day_boundary
    assert modified_registration_contract.functions.chainStarted().call() is True

    # Make 1 deposit with value MAX_DEPOSIT_AMOUNT and check that Eth2Genesis event is not triggered
    deposit_input = b'\x07' * 512
    modified_registration_contract.functions.deposit(
        deposit_input,
    ).transact({"value": max_deposit_amount})
    logs = log_filter.get_new_entries()
    assert len(logs) == 0
