import { Address, BigInt, Bytes } from "@graphprotocol/graph-ts"
import {
  TransferSingle,
  TransferBatch,
} from "../generated/NFT1155Credits/NFT1155Credits"
import { CreditTransfer, DailyPlanStats, ProtocolStats } from "../generated/schema"

const ZERO_ADDRESS = Address.fromString("0x0000000000000000000000000000000000000000")
const SECONDS_PER_DAY = 86400

function getTransferType(from: Address, to: Address): string {
  if (from == ZERO_ADDRESS) return "mint"
  if (to == ZERO_ADDRESS) return "burn"
  return "transfer"
}

function dayIdFromTimestamp(timestamp: BigInt): string {
  let dayTimestamp = timestamp.toI32() / SECONDS_PER_DAY
  let year = 1970
  let days = dayTimestamp

  // Approximate year calculation
  while (true) {
    let daysInYear = 365
    if (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) daysInYear = 366
    if (days < daysInYear) break
    days -= daysInYear
    year++
  }

  // Approximate month/day
  let monthDays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  if (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) monthDays[1] = 29
  let month = 1
  for (let i = 0; i < 12; i++) {
    if (days < monthDays[i]) break
    days -= monthDays[i]
    month++
  }
  let day = days + 1

  let y = year.toString()
  let m = month < 10 ? "0" + month.toString() : month.toString()
  let d = day < 10 ? "0" + day.toString() : day.toString()
  return y + "-" + m + "-" + d
}

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

function updateDailyStats(
  timestamp: BigInt,
  planId: BigInt,
  transferType: string,
  amount: BigInt
): void {
  let dateStr = dayIdFromTimestamp(timestamp)
  let id = dateStr + "-" + planId.toString()
  let daily = DailyPlanStats.load(id)
  if (daily == null) {
    daily = new DailyPlanStats(id)
    daily.date = dateStr
    daily.planId = planId
    daily.mintCount = 0
    daily.burnCount = 0
    daily.transferCount = 0
    daily.creditsMinted = BigInt.zero()
    daily.creditsBurned = BigInt.zero()
    daily.creditsTransferred = BigInt.zero()
  }

  if (transferType == "mint") {
    daily.mintCount += 1
    daily.creditsMinted = daily.creditsMinted.plus(amount)
  } else if (transferType == "burn") {
    daily.burnCount += 1
    daily.creditsBurned = daily.creditsBurned.plus(amount)
  } else {
    daily.transferCount += 1
    daily.creditsTransferred = daily.creditsTransferred.plus(amount)
  }

  daily.save()
}

export function handleTransferSingle(event: TransferSingle): void {
  let transferType = getTransferType(event.params.from, event.params.to)

  let entity = new CreditTransfer(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  )
  entity.type = transferType
  entity.operator = event.params.operator
  entity.from = event.params.from
  entity.to = event.params.to
  entity.planId = event.params.id
  entity.amount = event.params.value
  entity.blockNumber = event.block.number
  entity.blockTimestamp = event.block.timestamp
  entity.transactionHash = event.transaction.hash
  entity.save()

  // Update daily stats
  updateDailyStats(event.block.timestamp, event.params.id, transferType, event.params.value)

  // Update protocol stats
  let stats = getOrCreateProtocolStats()
  if (transferType == "mint") {
    stats.totalMints += 1
    stats.totalCreditsMinted = stats.totalCreditsMinted.plus(event.params.value)
  } else if (transferType == "burn") {
    stats.totalBurns += 1
    stats.totalCreditsBurned = stats.totalCreditsBurned.plus(event.params.value)
  }
  stats.save()
}

export function handleTransferBatch(event: TransferBatch): void {
  let transferType = getTransferType(event.params.from, event.params.to)
  let ids = event.params.ids
  let values = event.params.values

  for (let i = 0; i < ids.length; i++) {
    let entity = new CreditTransfer(
      event.transaction.hash.concatI32(event.logIndex.toI32() * 1000 + i)
    )
    entity.type = transferType
    entity.operator = event.params.operator
    entity.from = event.params.from
    entity.to = event.params.to
    entity.planId = ids[i]
    entity.amount = values[i]
    entity.blockNumber = event.block.number
    entity.blockTimestamp = event.block.timestamp
    entity.transactionHash = event.transaction.hash
    entity.save()

    updateDailyStats(event.block.timestamp, ids[i], transferType, values[i])

    let stats = getOrCreateProtocolStats()
    if (transferType == "mint") {
      stats.totalMints += 1
      stats.totalCreditsMinted = stats.totalCreditsMinted.plus(values[i])
    } else if (transferType == "burn") {
      stats.totalBurns += 1
      stats.totalCreditsBurned = stats.totalCreditsBurned.plus(values[i])
    }
    stats.save()
  }
}
