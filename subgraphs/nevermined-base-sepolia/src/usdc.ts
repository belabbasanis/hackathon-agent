import { Address, BigDecimal, BigInt, Bytes } from "@graphprotocol/graph-ts"
import { Transfer } from "../generated/USDC/ERC20"
import { USDCPayment, ProtocolStats } from "../generated/schema"

const PAYMENTS_VAULT = Address.fromString("0x47A72d7094c4c5B0566E159579DBD79220A0EA24")
const USDC_DECIMALS = BigDecimal.fromString("1000000") // 6 decimals

function getOrCreateProtocolStats(): ProtocolStats {
  let stats = ProtocolStats.load("global")
  if (stats == null) {
    stats = new ProtocolStats("global")
    stats.totalMints = 0
    stats.totalBurns = 0
    stats.totalCreditsMinted = BigInt.zero()
    stats.totalCreditsBurned = BigInt.zero()
    stats.totalUSDCVolume = BigInt.zero().toBigDecimal()
    stats.totalAgreements = 0
    stats.totalFulfilledConditions = 0
  }
  return stats
}

export function handleUSDCTransfer(event: Transfer): void {
  // Only index transfers TO the PaymentsVault
  if (event.params.to != PAYMENTS_VAULT) return

  let usdcAmount = event.params.value.toBigDecimal().div(USDC_DECIMALS)

  let entity = new USDCPayment(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  )
  entity.from = event.params.from
  entity.amount = usdcAmount
  entity.rawAmount = event.params.value
  entity.blockNumber = event.block.number
  entity.blockTimestamp = event.block.timestamp
  entity.transactionHash = event.transaction.hash
  entity.save()

  let stats = getOrCreateProtocolStats()
  stats.totalUSDCVolume = stats.totalUSDCVolume.plus(usdcAmount)
  stats.save()
}
