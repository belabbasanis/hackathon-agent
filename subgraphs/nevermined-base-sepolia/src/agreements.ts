import { BigInt, Bytes } from "@graphprotocol/graph-ts"
import {
  AgreementRegistered,
  ConditionUpdated as ConditionUpdatedEvent,
} from "../generated/AgreementsStore/AgreementsStore"
import { Agreement, ConditionUpdate, ProtocolStats } from "../generated/schema"

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

export function handleAgreementRegistered(event: AgreementRegistered): void {
  let entity = new Agreement(event.params.agreementId)
  entity.creator = event.params.creator
  entity.blockNumber = event.block.number
  entity.blockTimestamp = event.block.timestamp
  entity.transactionHash = event.transaction.hash
  entity.save()

  let stats = getOrCreateProtocolStats()
  stats.totalAgreements += 1
  stats.save()
}

export function handleConditionUpdated(event: ConditionUpdatedEvent): void {
  let entity = new ConditionUpdate(
    event.transaction.hash.concatI32(event.logIndex.toI32())
  )
  entity.agreement = event.params.agreementId
  entity.conditionId = event.params.conditionId
  entity.state = event.params.state
  entity.blockNumber = event.block.number
  entity.blockTimestamp = event.block.timestamp
  entity.transactionHash = event.transaction.hash
  entity.save()

  // State 2 = Fulfilled
  if (event.params.state == 2) {
    let stats = getOrCreateProtocolStats()
    stats.totalFulfilledConditions += 1
    stats.save()
  }
}
