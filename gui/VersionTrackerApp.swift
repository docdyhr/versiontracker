//
//  VersionTrackerApp.swift
//  VersionTracker
//
//  Created by VersionTracker Team on 2024-01-15.
//  Copyright © 2024 VersionTracker. All rights reserved.
//

import SwiftUI
import Combine
import Foundation

@main
struct VersionTrackerApp: App {
    @StateObject private var appManager = AppManager()
    @StateObject private var settingsManager = SettingsManager()
    @StateObject private var notificationManager = NotificationManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appManager)
                .environmentObject(settingsManager)
                .environmentObject(notificationManager)
                .onAppear {
                    setupInitialState()
                }
        }
        .windowStyle(DefaultWindowStyle())
        .windowResizability(.contentSize)
        .commands {
            VersionTrackerCommands()
        }

        Settings {
            SettingsView()
                .environmentObject(settingsManager)
                .environmentObject(appManager)
        }

        MenuBarExtra("VersionTracker", systemImage: "arrow.triangle.2.circlepath") {
            MenuBarView()
                .environmentObject(appManager)
                .environmentObject(settingsManager)
        }
    }

    private func setupInitialState() {
        // Initialize notification system
        notificationManager.requestPermission()

        // Start background monitoring if enabled
        if settingsManager.backgroundMonitoring {
            appManager.startBackgroundScanning()
        }

        // Load cached data
        appManager.loadCachedData()
    }
}

// MARK: - Content View
struct ContentView: View {
    @EnvironmentObject private var appManager: AppManager
    @EnvironmentObject private var settingsManager: SettingsManager
    @State private var selectedTab: TabSelection = .applications
    @State private var searchText = ""
    @State private var showingProgress = false

    enum TabSelection: CaseIterable {
        case applications, recommendations, updates, analytics

        var title: String {
            switch self {
            case .applications: return "Applications"
            case .recommendations: return "Recommendations"
            case .updates: return "Updates"
            case .analytics: return "Analytics"
            }
        }

        var systemImage: String {
            switch self {
            case .applications: return "app.badge"
            case .recommendations: return "lightbulb"
            case .updates: return "arrow.clockwise"
            case .analytics: return "chart.bar"
            }
        }
    }

    var body: some View {
        NavigationSplitView {
            // Sidebar
            List(TabSelection.allCases, id: \.self, selection: $selectedTab) { tab in
                NavigationLink(value: tab) {
                    Label(tab.title, systemImage: tab.systemImage)
                }
            }
            .navigationTitle("VersionTracker")
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 250)
        } detail: {
            // Main content
            VStack {
                // Search bar
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.secondary)
                    TextField("Search applications...", text: $searchText)
                        .textFieldStyle(.roundedBorder)

                    Button(action: refreshData) {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(appManager.isLoading)
                }
                .padding()

                // Tab content
                TabContentView(selectedTab: selectedTab, searchText: searchText)
            }
            .overlay(alignment: .center) {
                if showingProgress {
                    ProgressOverlay()
                }
            }
        }
        .onReceive(appManager.$isLoading) { isLoading in
            withAnimation {
                showingProgress = isLoading
            }
        }
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button("Scan Applications") {
                    Task {
                        await appManager.scanApplications()
                    }
                }
                .disabled(appManager.isLoading)

                Button("Get Recommendations") {
                    Task {
                        await appManager.generateRecommendations()
                    }
                }
                .disabled(appManager.isLoading)
            }
        }
    }

    private func refreshData() {
        Task {
            await appManager.refreshAllData()
        }
    }
}

// MARK: - Tab Content View
struct TabContentView: View {
    let selectedTab: ContentView.TabSelection
    let searchText: String
    @EnvironmentObject private var appManager: AppManager

    var body: some View {
        switch selectedTab {
        case .applications:
            ApplicationsView(searchText: searchText)
        case .recommendations:
            RecommendationsView(searchText: searchText)
        case .updates:
            UpdatesView(searchText: searchText)
        case .analytics:
            AnalyticsView()
        }
    }
}

// MARK: - Applications View
struct ApplicationsView: View {
    let searchText: String
    @EnvironmentObject private var appManager: AppManager
    @State private var sortOrder: SortOrder = .name
    @State private var filterOption: FilterOption = .all

    enum SortOrder: String, CaseIterable {
        case name = "Name"
        case version = "Version"
        case lastUpdated = "Last Updated"
        case size = "Size"
    }

    enum FilterOption: String, CaseIterable {
        case all = "All Applications"
        case nonAppStore = "Non-App Store"
        case outdated = "Outdated"
        case hasRecommendations = "Has Recommendations"
    }

    var filteredApplications: [Application] {
        var apps = appManager.applications

        // Apply search filter
        if !searchText.isEmpty {
            apps = apps.filter { app in
                app.name.localizedCaseInsensitiveContains(searchText) ||
                app.developer.localizedCaseInsensitiveContains(searchText)
            }
        }

        // Apply category filter
        switch filterOption {
        case .all:
            break
        case .nonAppStore:
            apps = apps.filter { !$0.isAppStoreApp }
        case .outdated:
            apps = apps.filter { $0.hasUpdate }
        case .hasRecommendations:
            apps = apps.filter { appManager.hasRecommendation(for: $0) }
        }

        // Apply sorting
        switch sortOrder {
        case .name:
            apps.sort { $0.name < $1.name }
        case .version:
            apps.sort { $0.version < $1.version }
        case .lastUpdated:
            apps.sort { $0.lastUpdated > $1.lastUpdated }
        case .size:
            apps.sort { $0.size > $1.size }
        }

        return apps
    }

    var body: some View {
        VStack {
            // Filter and sort controls
            HStack {
                Picker("Filter", selection: $filterOption) {
                    ForEach(FilterOption.allCases, id: \.self) { option in
                        Text(option.rawValue).tag(option)
                    }
                }
                .pickerStyle(.segmented)

                Spacer()

                Picker("Sort", selection: $sortOrder) {
                    ForEach(SortOrder.allCases, id: \.self) { order in
                        Text(order.rawValue).tag(order)
                    }
                }
                .pickerStyle(.menu)
            }
            .padding(.horizontal)

            // Applications list
            List(filteredApplications) { app in
                ApplicationRowView(application: app)
                    .contextMenu {
                        ApplicationContextMenu(application: app)
                    }
            }
            .listStyle(.inset)
        }
        .navigationTitle("Applications (\(filteredApplications.count))")
    }
}

// MARK: - Application Row View
struct ApplicationRowView: View {
    let application: Application
    @EnvironmentObject private var appManager: AppManager

    var body: some View {
        HStack {
            // App icon
            AsyncImage(url: application.iconURL) { image in
                image
                    .resizable()
                    .aspectRatio(contentMode: .fit)
            } placeholder: {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.3))
                    .overlay {
                        Image(systemName: "app")
                            .foregroundColor(.gray)
                    }
            }
            .frame(width: 32, height: 32)
            .cornerRadius(8)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(application.name)
                        .font(.headline)

                    if application.hasUpdate {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.orange)
                            .help("Update available")
                    }

                    if appManager.hasRecommendation(for: application) {
                        Image(systemName: "lightbulb.fill")
                            .foregroundColor(.yellow)
                            .help("Homebrew recommendation available")
                    }
                }

                HStack {
                    Text("v\(application.version)")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Spacer()

                    Text(application.developer)
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if application.isAppStoreApp {
                        Image(systemName: "app.badge")
                            .foregroundColor(.blue)
                            .help("App Store application")
                    }
                }
            }

            Spacer()

            VStack(alignment: .trailing) {
                Text(application.formattedSize)
                    .font(.caption)
                    .foregroundColor(.secondary)

                Text(application.formattedLastUpdated)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Recommendations View
struct RecommendationsView: View {
    let searchText: String
    @EnvironmentObject private var appManager: AppManager
    @State private var selectedRecommendation: Recommendation?
    @State private var showingInstallSheet = false

    var filteredRecommendations: [Recommendation] {
        var recommendations = appManager.recommendations

        if !searchText.isEmpty {
            recommendations = recommendations.filter { rec in
                rec.application.name.localizedCaseInsensitiveContains(searchText) ||
                rec.cask.name.localizedCaseInsensitiveContains(searchText)
            }
        }

        return recommendations.sorted { $0.confidence > $1.confidence }
    }

    var body: some View {
        VStack {
            if filteredRecommendations.isEmpty {
                ContentUnavailableView(
                    "No Recommendations",
                    systemImage: "lightbulb.slash",
                    description: Text("Generate recommendations to see Homebrew cask suggestions for your applications.")
                )
            } else {
                List(filteredRecommendations) { recommendation in
                    RecommendationRowView(recommendation: recommendation)
                        .onTapGesture {
                            selectedRecommendation = recommendation
                            showingInstallSheet = true
                        }
                }
                .listStyle(.inset)
            }
        }
        .navigationTitle("Recommendations (\(filteredRecommendations.count))")
        .sheet(isPresented: $showingInstallSheet) {
            if let recommendation = selectedRecommendation {
                InstallRecommendationSheet(recommendation: recommendation)
            }
        }
    }
}

// MARK: - Recommendation Row View
struct RecommendationRowView: View {
    let recommendation: Recommendation

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(recommendation.application.name)
                        .font(.headline)

                    Image(systemName: "arrow.right")
                        .foregroundColor(.secondary)

                    Text(recommendation.cask.name)
                        .font(.headline)
                        .foregroundColor(.blue)
                }

                Text(recommendation.cask.description)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)

                HStack {
                    ConfidenceIndicator(confidence: recommendation.confidence)

                    Spacer()

                    if recommendation.cask.autoUpdates {
                        Label("Auto-updates", systemImage: "arrow.clockwise")
                            .font(.caption2)
                            .foregroundColor(.green)
                    }
                }
            }

            Spacer()

            VStack {
                Button("Install") {
                    Task {
                        await installCask(recommendation.cask)
                    }
                }
                .buttonStyle(.borderedProminent)

                Button("Dismiss") {
                    dismissRecommendation(recommendation)
                }
                .buttonStyle(.bordered)
                .font(.caption)
            }
        }
        .padding(.vertical, 4)
    }

    private func installCask(_ cask: Cask) async {
        // Implementation for installing Homebrew cask
    }

    private func dismissRecommendation(_ recommendation: Recommendation) {
        // Implementation for dismissing recommendation
    }
}

// MARK: - Progress Overlay
struct ProgressOverlay: View {
    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)

            Text("Processing...")
                .font(.headline)
        }
        .padding(32)
        .background(Material.regular)
        .cornerRadius(16)
        .shadow(radius: 8)
    }
}

// MARK: - Confidence Indicator
struct ConfidenceIndicator: View {
    let confidence: Double

    private var color: Color {
        switch confidence {
        case 0.8...:
            return .green
        case 0.6...:
            return .yellow
        default:
            return .orange
        }
    }

    private var label: String {
        switch confidence {
        case 0.9...:
            return "Excellent match"
        case 0.8...:
            return "Great match"
        case 0.7...:
            return "Good match"
        case 0.6...:
            return "Fair match"
        default:
            return "Possible match"
        }
    }

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<5) { index in
                Circle()
                    .fill(index < Int(confidence * 5) ? color : Color.gray.opacity(0.3))
                    .frame(width: 8, height: 8)
            }

            Text(label)
                .font(.caption2)
                .foregroundColor(color)
        }
    }
}

// MARK: - Menu Bar View
struct MenuBarView: View {
    @EnvironmentObject private var appManager: AppManager
    @EnvironmentObject private var settingsManager: SettingsManager

    var body: some View {
        VStack {
            if appManager.hasUpdates {
                Button("Updates Available") {
                    // Open main app to updates tab
                }
                .foregroundColor(.orange)
            } else {
                Text("All applications up to date")
                    .foregroundColor(.secondary)
            }

            Divider()

            Button("Scan Now") {
                Task {
                    await appManager.scanApplications()
                }
            }

            Button("Open VersionTracker") {
                NSApp.activate(ignoringOtherApps: true)
            }

            Divider()

            Button("Quit") {
                NSApp.terminate(nil)
            }
        }
    }
}

// MARK: - Data Models
struct Application: Identifiable, Codable {
    let id = UUID()
    let name: String
    let version: String
    let developer: String
    let bundleIdentifier: String
    let path: String
    let size: Int64
    let lastUpdated: Date
    let isAppStoreApp: Bool
    let hasUpdate: Bool

    var iconURL: URL? {
        // Generate icon URL based on bundle identifier or path
        return nil
    }

    var formattedSize: String {
        ByteCountFormatter.string(fromByteCount: size, countStyle: .file)
    }

    var formattedLastUpdated: String {
        RelativeDateTimeFormatter().localizedString(for: lastUpdated, relativeTo: Date())
    }
}

struct Cask: Identifiable, Codable {
    let id = UUID()
    let name: String
    let fullName: String
    let description: String
    let version: String
    let homepage: String
    let autoUpdates: Bool
}

struct Recommendation: Identifiable {
    let id = UUID()
    let application: Application
    let cask: Cask
    let confidence: Double
    let reason: String
}

// MARK: - App Manager
@MainActor
class AppManager: ObservableObject {
    @Published var applications: [Application] = []
    @Published var recommendations: [Recommendation] = []
    @Published var isLoading = false
    @Published var error: String?

    private let pythonBridge = PythonBridge()

    var hasUpdates: Bool {
        applications.contains { $0.hasUpdate }
    }

    func hasRecommendation(for application: Application) -> Bool {
        recommendations.contains { $0.application.id == application.id }
    }

    func scanApplications() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let scannedApps = try await pythonBridge.scanApplications()
            applications = scannedApps
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    func generateRecommendations() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let newRecommendations = try await pythonBridge.generateRecommendations(for: applications)
            recommendations = newRecommendations
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    func refreshAllData() async {
        await scanApplications()
        await generateRecommendations()
    }

    func loadCachedData() {
        // Load from UserDefaults or Core Data
    }

    func startBackgroundScanning() {
        // Implementation for background scanning
    }
}

// MARK: - Settings Manager
class SettingsManager: ObservableObject {
    @Published var backgroundMonitoring = false
    @Published var notificationsEnabled = true
    @Published var autoCheckInterval: TimeInterval = 3600 // 1 hour
    @Published var confidenceThreshold = 0.7

    init() {
        loadSettings()
    }

    private func loadSettings() {
        // Load from UserDefaults
    }

    func saveSettings() {
        // Save to UserDefaults
    }
}

// MARK: - Notification Manager
class NotificationManager: ObservableObject {
    func requestPermission() {
        // Request notification permissions
    }

    func scheduleUpdateNotification(for applications: [Application]) {
        // Schedule notifications for available updates
    }
}

// MARK: - Python Bridge
class PythonBridge {
    func scanApplications() async throws -> [Application] {
        // Execute Python VersionTracker CLI and parse results
        // This would use Process to call the Python CLI
        return []
    }

    func generateRecommendations(for applications: [Application]) async throws -> [Recommendation] {
        // Execute Python VersionTracker CLI for recommendations
        return []
    }
}

// MARK: - Command Definitions
struct VersionTrackerCommands: Commands {
    var body: some Commands {
        CommandGroup(replacing: .appInfo) {
            Button("About VersionTracker") {
                // Show about window
            }
        }

        CommandGroup(after: .newItem) {
            Button("Scan Applications") {
                // Trigger scan
            }
            .keyboardShortcut("r", modifiers: .command)

            Button("Generate Recommendations") {
                // Trigger recommendations
            }
            .keyboardShortcut("g", modifiers: .command)
        }
    }
}

// MARK: - Context Menus and Supporting Views
struct ApplicationContextMenu: View {
    let application: Application

    var body: some View {
        Button("Show in Finder") {
            NSWorkspace.shared.selectFile(nil, inFileViewerRootedAtPath: application.path)
        }

        Button("Get Info") {
            // Show application info sheet
        }

        if !application.isAppStoreApp {
            Button("Add to Blacklist") {
                // Add to blacklist
            }
        }

        Divider()

        Button("Copy Path") {
            NSPasteboard.general.setString(application.path, forType: .string)
        }
    }
}

struct InstallRecommendationSheet: View {
    let recommendation: Recommendation
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 20) {
            HStack {
                Text("Install Homebrew Cask")
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button("Cancel") {
                    dismiss()
                }
            }

            HStack {
                VStack(alignment: .leading) {
                    Text("Current Application")
                        .font(.headline)
                    Text(recommendation.application.name)
                    Text("Version: \(recommendation.application.version)")
                        .foregroundColor(.secondary)
                }

                Image(systemName: "arrow.right")
                    .foregroundColor(.blue)

                VStack(alignment: .leading) {
                    Text("Homebrew Cask")
                        .font(.headline)
                    Text(recommendation.cask.name)
                    Text("Version: \(recommendation.cask.version)")
                        .foregroundColor(.secondary)
                }
            }

            Text(recommendation.cask.description)
                .padding()
                .background(Color.gray.opacity(0.1))
                .cornerRadius(8)

            HStack {
                Button("Install with Homebrew") {
                    // Install cask
                    dismiss()
                }
                .buttonStyle(.borderedProminent)

                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)
            }
        }
        .padding()
        .frame(width: 500, height: 300)
    }
}

struct SettingsView: View {
    @EnvironmentObject private var settingsManager: SettingsManager

    var body: some View {
        TabView {
            GeneralSettingsView()
                .tabItem { Label("General", systemImage: "gear") }

            NotificationSettingsView()
                .tabItem { Label("Notifications", systemImage: "bell") }

            AdvancedSettingsView()
                .tabItem { Label("Advanced", systemImage: "slider.horizontal.3") }
        }
        .frame(width: 450, height: 300)
    }
}

struct GeneralSettingsView: View {
    @EnvironmentObject private var settingsManager: SettingsManager

    var body: some View {
        Form {
            Toggle("Enable background monitoring", isOn: $settingsManager.backgroundMonitoring)

            HStack {
                Text("Check interval:")
                Picker("", selection: $settingsManager.autoCheckInterval) {
                    Text("15 minutes").tag(TimeInterval(900))
                    Text("30 minutes").tag(TimeInterval(1800))
                    Text("1 hour").tag(TimeInterval(3600))
                    Text("6 hours").tag(TimeInterval(21600))
                    Text("24 hours").tag(TimeInterval(86400))
                }
                .pickerStyle(.menu)
            }

            HStack {
                Text("Confidence threshold:")
                Slider(value: $settingsManager.confidenceThreshold, in: 0.5...1.0, step: 0.1)
                Text("\(Int(settingsManager.confidenceThreshold * 100))%")
            }
        }
        .padding()
    }
}

struct NotificationSettingsView: View {
    @EnvironmentObject private var settingsManager: SettingsManager

    var body: some View {
        Form {
            Toggle("Enable notifications", isOn: $settingsManager.notificationsEnabled)

            // Additional notification settings
        }
        .padding()
    }
}

struct AdvancedSettingsView: View {
    var body: some View {
        Form {
            // Advanced settings like Python path, cache settings, etc.
        }
        .padding()
    }
}

struct UpdatesView: View {
    let searchText: String

    var body: some View {
        Text("Updates view - Coming soon")
    }
}

struct AnalyticsView: View {
    var body: some View {
        Text("Analytics view - Coming soon")
    }
}
