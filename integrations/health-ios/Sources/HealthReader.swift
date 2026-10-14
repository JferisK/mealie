import Foundation
import HealthKit

struct Observation: Codable {
    let id: String
    let kind: String
    let value: Double
    let at: String
    let source: String
}

@MainActor
final class HealthReader {
    let store = HKHealthStore()
    private var observers: [HKObserverQuery] = []
    let quantities: [(HKQuantityTypeIdentifier, String, HKUnit)] = [
        (.bodyMass, "weight_kg", .gramUnit(with: .kilo)),
        (.height, "height_cm", .meterUnit(with: .centi)),
        (.bodyFatPercentage, "body_fat_percent", .percent())
    ]
    let daily: [(HKQuantityTypeIdentifier, String, HKUnit)] = [
        (.stepCount, "steps", .count()), (.activeEnergyBurned, "active_kcal", .kilocalorie()),
        (.basalEnergyBurned, "resting_kcal", .kilocalorie())
    ]
    var types: Set<HKObjectType> {
        var result = Set<HKObjectType>((quantities + daily).compactMap { HKQuantityType.quantityType(forIdentifier: $0.0) })
        result.insert(HKObjectType.workoutType())
        return result
    }
    private var nextAnchors: [String: String] = [:]
    private(set) var deletedIDs: [String] = []
    var anchorScope = ""

    func commitAnchors() throws {
        let data = try JSONEncoder().encode(nextAnchors)
        try Credentials.save(data.base64EncodedString(), key: "anchors:" + anchorScope)
    }
    func authorize() async throws {
        guard HKHealthStore.isHealthDataAvailable() else { throw BridgeError.message("HealthKit is unavailable on this device") }
        try await store.requestAuthorization(toShare: [], read: types)
    }
    func sampleObservations() async throws -> [Observation] {
        nextAnchors = [:]
        deletedIDs = []
        let now = Date()
        let since = Calendar.current.date(byAdding: .day, value: -90, to: now)!
        let iso = ISO8601DateFormatter()
        var result: [Observation] = []
        for (identifier, kind, unit) in quantities {
            let type = HKQuantityType.quantityType(forIdentifier: identifier)!
            let samples = try await changedSamples(type: type)
            for case let sample as HKQuantitySample in samples {
                guard sample.startDate >= since else { continue }
                let value = sample.quantity.doubleValue(for: unit) * (kind == "body_fat_percent" ? 100 : 1)
                result.append(Observation(id: sample.uuid.uuidString, kind: kind, value: value,
                    at: iso.string(from: sample.startDate), source: sample.sourceRevision.source.bundleIdentifier))
            }
        }
        // HealthKit statistics reconcile overlapping phone/watch sources. Never sum raw samples ourselves.
        let start = Calendar.current.startOfDay(for: Calendar.current.date(byAdding: .day, value: -28, to: now)!)
        for (identifier, kind, unit) in daily {
            let type = HKQuantityType.quantityType(forIdentifier: identifier)!
            let stats: HKStatisticsCollection = try await withCheckedThrowingContinuation { continuation in
                let query = HKStatisticsCollectionQuery(quantityType: type,
                    quantitySamplePredicate: HKQuery.predicateForSamples(withStart: start, end: now),
                    options: .cumulativeSum, anchorDate: start, intervalComponents: DateComponents(day: 1))
                query.initialResultsHandler = { _, collection, error in
                    if let error { continuation.resume(throwing: error) }
                    else if let collection { continuation.resume(returning: collection) }
                    else { continuation.resume(throwing: BridgeError.message("No statistics returned")) }
                }
                store.execute(query)
            }
            stats.enumerateStatistics(from: start, to: now) { statistic, _ in
                if let sum = statistic.sumQuantity() {
                    let time = iso.string(from: statistic.startDate)
                    result.append(Observation(id: "daily:\(kind):\(time)", kind: kind,
                        value: sum.doubleValue(for: unit), at: time, source: "HealthKit.reconciled.daily"))
                }
            }
        }
        let workouts = try await changedSamples(type: HKObjectType.workoutType())
        for case let workout as HKWorkout in workouts {
            guard workout.startDate >= since else { continue }
            result.append(Observation(id: workout.uuid.uuidString, kind: "workout_minutes", value: workout.duration / 60,
                at: iso.string(from: workout.startDate), source: workout.sourceRevision.source.bundleIdentifier))
        }
        return result
    }
    private func changedSamples(type: HKSampleType) async throws -> [HKSample] {
        let encoded = Credentials.read("anchors:" + anchorScope)
        let saved = Data(base64Encoded: encoded).flatMap { try? JSONDecoder().decode([String: String].self, from: $0) } ?? [:]
        let anchorData = saved[type.identifier].flatMap { Data(base64Encoded: $0) }
        var anchor = try anchorData.flatMap { try NSKeyedUnarchiver.unarchivedObject(ofClass: HKQueryAnchor.self, from: $0) }
        var result: [HKSample] = []
        // Page through changes; only real HealthKit tombstones remove records. Revoked read access is not deletion.
        while true {
            let page: ([HKSample], [HKDeletedObject], HKQueryAnchor?) = try await withCheckedThrowingContinuation { continuation in
                let query = HKAnchoredObjectQuery(type: type, predicate: nil, anchor: anchor, limit: 500) { _, samples, deleted, next, error in
                    if let error { continuation.resume(throwing: error) }
                    else { continuation.resume(returning: (samples ?? [], deleted ?? [], next)) }
                }
                store.execute(query)
            }
            result.append(contentsOf: page.0)
            deletedIDs.append(contentsOf: page.1.map { $0.uuid.uuidString })
            anchor = page.2
            if page.0.count + page.1.count < 500 { break }
        }
        if let anchor {
            nextAnchors[type.identifier] = try NSKeyedArchiver.archivedData(withRootObject: anchor, requiringSecureCoding: true).base64EncodedString()
        } else if let previous = saved[type.identifier] {
            nextAnchors[type.identifier] = previous
        }
        return result
    }
    func observe(onChange: @escaping @MainActor () async -> Void) async {
        guard observers.isEmpty else { return }
        for type in types.compactMap({ $0 as? HKSampleType }) {
            let query = HKObserverQuery(sampleType: type, predicate: nil) { _, completion, error in
                guard error == nil else { completion(); return }
                Task { @MainActor in await onChange(); completion() }
            }
            observers.append(query)
            store.execute(query)
            try? await store.enableBackgroundDelivery(for: type, frequency: .daily)
        }
    }
    func stop() async {
        observers.forEach { store.stop($0) }
        observers.removeAll()
        try? await store.disableAllBackgroundDelivery()
    }
}
