"""
Comprehensive analytics and monitoring system for VersionTracker.

This module provides detailed analytics, usage tracking, performance monitoring,
and business intelligence capabilities for understanding application management
patterns and system performance.
"""

import json
import logging
import platform
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import psutil

from versiontracker.exceptions import VersionTrackerError

logger = logging.getLogger(__name__)

__all__ = [
    "AnalyticsEngine",
    "MetricsCollector",
    "UsageTracker",
    "PerformanceMonitor",
    "EventLogger",
    "AnalyticsReport",
    "SystemMetrics",
    "UserBehaviorAnalytics",
]


class AnalyticsError(VersionTrackerError):
    """Raised when analytics operations fail."""

    pass


@dataclass
class SystemMetrics:
    """System performance metrics."""

    timestamp: float
    cpu_percent: float
    memory_used_mb: float
    memory_percent: float
    disk_usage_percent: float
    network_io_bytes: int
    process_count: int
    load_average: list[float]
    python_version: str
    platform_info: str
    versiontracker_version: str


@dataclass
class UsageEvent:
    """User interaction event."""

    event_id: str
    timestamp: float
    event_type: str
    command: str
    duration_ms: int
    success: bool
    error_code: str | None
    app_count: int
    cask_count: int
    recommendations_count: int
    user_id_hash: str
    session_id: str
    metadata: dict[str, Any]


@dataclass
class PerformanceEvent:
    """Performance monitoring event."""

    event_id: str
    timestamp: float
    operation: str
    duration_ms: int
    memory_delta_mb: float
    cpu_peak_percent: float
    success: bool
    error_message: str | None
    input_size: int
    output_size: int
    cache_hit: bool
    metadata: dict[str, Any]


class EventLogger:
    """High-performance event logging with SQLite backend."""

    def __init__(self, db_path: Path | None = None):
        """Initialize event logger."""
        self.db_path = db_path or Path.home() / ".config" / "versiontracker" / "analytics.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._batch_events = []
        self._batch_size = 100
        self._last_flush = time.time()
        self._flush_interval = 30  # seconds

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database schema."""
        with self._get_connection() as conn:
            # System metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_percent REAL,
                    memory_used_mb REAL,
                    memory_percent REAL,
                    disk_usage_percent REAL,
                    network_io_bytes INTEGER,
                    process_count INTEGER,
                    load_average TEXT,
                    python_version TEXT,
                    platform_info TEXT,
                    versiontracker_version TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Usage events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    command TEXT NOT NULL,
                    duration_ms INTEGER,
                    success BOOLEAN,
                    error_code TEXT,
                    app_count INTEGER,
                    cask_count INTEGER,
                    recommendations_count INTEGER,
                    user_id_hash TEXT,
                    session_id TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Performance events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp REAL NOT NULL,
                    operation TEXT NOT NULL,
                    duration_ms INTEGER,
                    memory_delta_mb REAL,
                    cpu_peak_percent REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    input_size INTEGER,
                    output_size INTEGER,
                    cache_hit BOOLEAN,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_timestamp ON usage_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_events_command ON usage_events(command)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_events_timestamp ON performance_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_events_operation ON performance_events(operation)")

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise AnalyticsError(f"Database error: {e}") from e
        finally:
            if conn:
                conn.close()

    def log_system_metrics(self, metrics: SystemMetrics):
        """Log system performance metrics."""
        with self._lock:
            self._batch_events.append(("system_metrics", metrics))
            self._maybe_flush()

    def log_usage_event(self, event: UsageEvent):
        """Log user interaction event."""
        with self._lock:
            self._batch_events.append(("usage_events", event))
            self._maybe_flush()

    def log_performance_event(self, event: PerformanceEvent):
        """Log performance monitoring event."""
        with self._lock:
            self._batch_events.append(("performance_events", event))
            self._maybe_flush()

    def _maybe_flush(self):
        """Flush events if batch is full or enough time has passed."""
        current_time = time.time()
        should_flush = (
            len(self._batch_events) >= self._batch_size or (current_time - self._last_flush) >= self._flush_interval
        )

        if should_flush:
            self._flush_events()

    def _flush_events(self):
        """Flush batched events to database."""
        if not self._batch_events:
            return

        try:
            with self._get_connection() as conn:
                for table, event in self._batch_events:
                    if table == "system_metrics":
                        self._insert_system_metrics(conn, event)
                    elif table == "usage_events":
                        self._insert_usage_event(conn, event)
                    elif table == "performance_events":
                        self._insert_performance_event(conn, event)

                conn.commit()

            self._batch_events.clear()
            self._last_flush = time.time()

        except Exception as e:
            logger.error(f"Failed to flush events to database: {e}")

    def _insert_system_metrics(self, conn: sqlite3.Connection, metrics: SystemMetrics):
        """Insert system metrics into database."""
        conn.execute(
            """
            INSERT INTO system_metrics (
                timestamp, cpu_percent, memory_used_mb, memory_percent,
                disk_usage_percent, network_io_bytes, process_count,
                load_average, python_version, platform_info, versiontracker_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metrics.timestamp,
                metrics.cpu_percent,
                metrics.memory_used_mb,
                metrics.memory_percent,
                metrics.disk_usage_percent,
                metrics.network_io_bytes,
                metrics.process_count,
                json.dumps(metrics.load_average),
                metrics.python_version,
                metrics.platform_info,
                metrics.versiontracker_version,
            ),
        )

    def _insert_usage_event(self, conn: sqlite3.Connection, event: UsageEvent):
        """Insert usage event into database."""
        conn.execute(
            """
            INSERT INTO usage_events (
                event_id, timestamp, event_type, command, duration_ms,
                success, error_code, app_count, cask_count,
                recommendations_count, user_id_hash, session_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event.event_id,
                event.timestamp,
                event.event_type,
                event.command,
                event.duration_ms,
                event.success,
                event.error_code,
                event.app_count,
                event.cask_count,
                event.recommendations_count,
                event.user_id_hash,
                event.session_id,
                json.dumps(event.metadata),
            ),
        )

    def _insert_performance_event(self, conn: sqlite3.Connection, event: PerformanceEvent):
        """Insert performance event into database."""
        conn.execute(
            """
            INSERT INTO performance_events (
                event_id, timestamp, operation, duration_ms, memory_delta_mb,
                cpu_peak_percent, success, error_message, input_size,
                output_size, cache_hit, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event.event_id,
                event.timestamp,
                event.operation,
                event.duration_ms,
                event.memory_delta_mb,
                event.cpu_peak_percent,
                event.success,
                event.error_message,
                event.input_size,
                event.output_size,
                event.cache_hit,
                json.dumps(event.metadata),
            ),
        )

    def get_recent_metrics(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get recent system metrics."""
        cutoff_time = time.time() - (hours * 3600)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM system_metrics
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1000
            """,
                (cutoff_time,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_usage_summary(self, days: int = 7) -> dict[str, Any]:
        """Get usage summary for the specified period."""
        cutoff_time = time.time() - (days * 24 * 3600)

        with self._get_connection() as conn:
            # Command frequency
            cursor = conn.execute(
                """
                SELECT command, COUNT(*) as count, AVG(duration_ms) as avg_duration
                FROM usage_events
                WHERE timestamp > ?
                GROUP BY command
                ORDER BY count DESC
            """,
                (cutoff_time,),
            )
            command_stats = [dict(row) for row in cursor.fetchall()]

            # Success rate
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_events,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_events,
                    AVG(duration_ms) as avg_duration
                FROM usage_events
                WHERE timestamp > ?
            """,
                (cutoff_time,),
            )
            overall_stats = dict(cursor.fetchone())

            # Error frequency
            cursor = conn.execute(
                """
                SELECT error_code, COUNT(*) as count
                FROM usage_events
                WHERE timestamp > ? AND error_code IS NOT NULL
                GROUP BY error_code
                ORDER BY count DESC
            """,
                (cutoff_time,),
            )
            error_stats = [dict(row) for row in cursor.fetchall()]

            return {
                "period_days": days,
                "command_statistics": command_stats,
                "overall_statistics": overall_stats,
                "error_statistics": error_stats,
            }

    def flush(self):
        """Manually flush all pending events."""
        with self._lock:
            self._flush_events()


class MetricsCollector:
    """Collect system and application metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = time.time()
        self.session_id = str(uuid4())

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics."""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Network I/O
            network_io = psutil.net_io_counters()
            network_bytes = network_io.bytes_sent + network_io.bytes_recv

            # Load average (Unix systems)
            try:
                load_avg = list(psutil.getloadavg())
            except AttributeError:
                load_avg = [0.0, 0.0, 0.0]

            # Version info
            from versiontracker import __version__

            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io_bytes=network_bytes,
                process_count=len(psutil.pids()),
                load_average=load_avg,
                python_version=platform.python_version(),
                platform_info=platform.platform(),
                versiontracker_version=__version__,
            )

        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
            # Return minimal metrics
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_used_mb=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_io_bytes=0,
                process_count=0,
                load_average=[0.0, 0.0, 0.0],
                python_version=platform.python_version(),
                platform_info=platform.platform(),
                versiontracker_version="unknown",
            )

    def get_user_id_hash(self) -> str:
        """Get anonymized user identifier."""
        import getpass
        import hashlib

        try:
            username = getpass.getuser()
            hostname = platform.node()
            user_string = f"{username}@{hostname}"
            return hashlib.sha256(user_string.encode()).hexdigest()[:16]
        except Exception:
            return "anonymous"


class UsageTracker:
    """Track user interactions and behavior patterns."""

    def __init__(self, event_logger: EventLogger):
        """Initialize usage tracker."""
        self.event_logger = event_logger
        self.metrics_collector = MetricsCollector()
        self.active_operations = {}

    @contextmanager
    def track_operation(self, command: str, metadata: dict[str, Any] | None = None):
        """Context manager to track operation execution."""
        operation_id = str(uuid4())
        start_time = time.time()
        start_memory = self._get_memory_usage()

        operation_data = {
            "command": command,
            "start_time": start_time,
            "start_memory": start_memory,
            "metadata": metadata or {},
        }

        self.active_operations[operation_id] = operation_data

        success = False
        error_code = None

        try:
            yield operation_data
            success = True
        except Exception as e:
            error_code = getattr(e, "error_code", None) or e.__class__.__name__
            raise
        finally:
            end_time = time.time()

            duration_ms = int((end_time - start_time) * 1000)

            # Create usage event
            event = UsageEvent(
                event_id=str(uuid4()),
                timestamp=start_time,
                event_type="command_execution",
                command=command,
                duration_ms=duration_ms,
                success=success,
                error_code=error_code,
                app_count=operation_data["metadata"].get("app_count", 0),
                cask_count=operation_data["metadata"].get("cask_count", 0),
                recommendations_count=operation_data["metadata"].get("recommendations_count", 0),
                user_id_hash=self.metrics_collector.get_user_id_hash(),
                session_id=self.metrics_collector.session_id,
                metadata=operation_data["metadata"],
            )

            self.event_logger.log_usage_event(event)

            # Clean up
            self.active_operations.pop(operation_id, None)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0


class PerformanceMonitor:
    """Monitor performance of specific operations."""

    def __init__(self, event_logger: EventLogger):
        """Initialize performance monitor."""
        self.event_logger = event_logger

    @contextmanager
    def monitor_operation(self, operation: str, input_size: int = 0, metadata: dict[str, Any] | None = None):
        """Monitor performance of an operation."""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        cpu_monitor = self._CPUMonitor()
        cpu_monitor.start()

        success = False
        error_message = None
        output_size = 0
        cache_hit = False

        try:
            yield {
                "set_output_size": lambda size: setattr(self, "_output_size", size),
                "set_cache_hit": lambda hit: setattr(self, "_cache_hit", hit),
            }
            success = True
            output_size = getattr(self, "_output_size", 0)
            cache_hit = getattr(self, "_cache_hit", False)
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            peak_cpu = cpu_monitor.stop()

            duration_ms = int((end_time - start_time) * 1000)
            memory_delta = end_memory - start_memory

            event = PerformanceEvent(
                event_id=str(uuid4()),
                timestamp=start_time,
                operation=operation,
                duration_ms=duration_ms,
                memory_delta_mb=memory_delta,
                cpu_peak_percent=peak_cpu,
                success=success,
                error_message=error_message,
                input_size=input_size,
                output_size=output_size,
                cache_hit=cache_hit,
                metadata=metadata or {},
            )

            self.event_logger.log_performance_event(event)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    class _CPUMonitor:
        """Helper class to monitor CPU usage."""

        def __init__(self):
            self.peak_cpu = 0.0
            self.monitoring = False
            self._stop_event = threading.Event()
            self._thread = None

        def start(self):
            """Start CPU monitoring."""
            self.monitoring = True
            self._thread = threading.Thread(target=self._monitor_cpu)
            self._thread.daemon = True
            self._thread.start()

        def stop(self) -> float:
            """Stop CPU monitoring and return peak usage."""
            self.monitoring = False
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=1.0)
            return self.peak_cpu

        def _monitor_cpu(self):
            """Monitor CPU usage in background thread."""
            while self.monitoring and not self._stop_event.is_set():
                try:
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    self.peak_cpu = max(self.peak_cpu, cpu_percent)
                except Exception:
                    pass
                time.sleep(0.05)


class UserBehaviorAnalytics:
    """Analyze user behavior patterns."""

    def __init__(self, event_logger: EventLogger):
        """Initialize behavior analytics."""
        self.event_logger = event_logger

    def analyze_command_patterns(self, days: int = 30) -> dict[str, Any]:
        """Analyze command usage patterns."""
        cutoff_time = time.time() - (days * 24 * 3600)

        with self.event_logger._get_connection() as conn:
            # Command sequence analysis
            cursor = conn.execute(
                """
                SELECT command, timestamp
                FROM usage_events
                WHERE timestamp > ?
                ORDER BY timestamp
            """,
                (cutoff_time,),
            )

            commands = [(row[0], row[1]) for row in cursor.fetchall()]

            # Analyze sequences
            sequences = []
            current_sequence = []
            last_timestamp = 0

            for command, timestamp in commands:
                if timestamp - last_timestamp > 300:  # 5 minute gap
                    if len(current_sequence) > 1:
                        sequences.append(current_sequence)
                    current_sequence = [command]
                else:
                    current_sequence.append(command)
                last_timestamp = timestamp

            if len(current_sequence) > 1:
                sequences.append(current_sequence)

            # Find common patterns
            pattern_counts = {}
            for sequence in sequences:
                for i in range(len(sequence) - 1):
                    pattern = f"{sequence[i]} -> {sequence[i + 1]}"
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

            return {
                "total_sequences": len(sequences),
                "common_patterns": sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "average_sequence_length": sum(len(seq) for seq in sequences) / len(sequences) if sequences else 0,
            }

    def get_performance_insights(self, days: int = 7) -> dict[str, Any]:
        """Get performance insights and recommendations."""
        cutoff_time = time.time() - (days * 24 * 3600)

        with self.event_logger._get_connection() as conn:
            # Slow operations
            cursor = conn.execute(
                """
                SELECT operation, AVG(duration_ms) as avg_duration, COUNT(*) as count
                FROM performance_events
                WHERE timestamp > ? AND success = 1
                GROUP BY operation
                HAVING count >= 5
                ORDER BY avg_duration DESC
            """,
                (cutoff_time,),
            )

            slow_operations = [dict(row) for row in cursor.fetchall()]

            # Memory intensive operations
            cursor = conn.execute(
                """
                SELECT operation, AVG(memory_delta_mb) as avg_memory, COUNT(*) as count
                FROM performance_events
                WHERE timestamp > ? AND success = 1 AND memory_delta_mb > 0
                GROUP BY operation
                HAVING count >= 5
                ORDER BY avg_memory DESC
            """,
                (cutoff_time,),
            )

            memory_intensive = [dict(row) for row in cursor.fetchall()]

            # Cache hit rates
            cursor = conn.execute(
                """
                SELECT operation,
                    COUNT(*) as total_ops,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                FROM performance_events
                WHERE timestamp > ?
                GROUP BY operation
                HAVING total_ops >= 10
            """,
                (cutoff_time,),
            )

            cache_stats = []
            for row in cursor.fetchall():
                operation, total, hits = row
                hit_rate = (hits / total) * 100 if total > 0 else 0
                cache_stats.append(
                    {
                        "operation": operation,
                        "total_operations": total,
                        "cache_hits": hits,
                        "hit_rate_percent": hit_rate,
                    }
                )

            cache_stats.sort(key=lambda x: x["hit_rate_percent"])

            return {
                "slow_operations": slow_operations[:5],
                "memory_intensive_operations": memory_intensive[:5],
                "cache_performance": cache_stats,
                "recommendations": self._generate_performance_recommendations(
                    slow_operations, memory_intensive, cache_stats
                ),
            }

    def _generate_performance_recommendations(
        self, slow_ops: list[dict], memory_ops: list[dict], cache_stats: list[dict]
    ) -> list[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        # Slow operations
        if slow_ops and slow_ops[0]["avg_duration"] > 5000:  # > 5 seconds
            recommendations.append(
                f"Consider optimizing '{slow_ops[0]['operation']}' operation "
                f"(average duration: {slow_ops[0]['avg_duration']:.0f}ms)"
            )

        # Memory usage
        if memory_ops and memory_ops[0]["avg_memory"] > 100:  # > 100MB
            recommendations.append(
                f"Operation '{memory_ops[0]['operation']}' uses significant memory "
                f"({memory_ops[0]['avg_memory']:.1f}MB average). Consider memory optimization."
            )

        # Cache performance
        low_cache_ops = [op for op in cache_stats if op["hit_rate_percent"] < 50 and op["total_operations"] > 50]
        if low_cache_ops:
            recommendations.append(
                f"Low cache hit rate for '{low_cache_ops[0]['operation']}' "
                f"({low_cache_ops[0]['hit_rate_percent']:.1f}%). Review caching strategy."
            )

        return recommendations


class AnalyticsReport:
    """Generate comprehensive analytics reports."""

    def __init__(self, event_logger: EventLogger):
        """Initialize analytics report generator."""
        self.event_logger = event_logger
        self.behavior_analytics = UserBehaviorAnalytics(event_logger)

    def generate_summary_report(self, days: int = 7) -> dict[str, Any]:
        """Generate comprehensive summary report."""
        # Usage statistics
        usage_summary = self.event_logger.get_usage_summary(days)

        # Performance insights
        performance_insights = self.behavior_analytics.get_performance_insights(days)

        # Command patterns
        command_patterns = self.behavior_analytics.analyze_command_patterns(days)

        # System health
        recent_metrics = self.event_logger.get_recent_metrics(days * 24)

        system_health = self._analyze_system_health(recent_metrics) if recent_metrics else {}

        return {
            "report_period_days": days,
            "generated_at": datetime.now().isoformat(),
            "usage_statistics": usage_summary,
            "performance_insights": performance_insights,
            "command_patterns": command_patterns,
            "system_health": system_health,
            "recommendations": self._generate_overall_recommendations(
                usage_summary, performance_insights, command_patterns
            ),
        }

    def _analyze_system_health(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze system health from metrics."""
        if not metrics:
            return {}

        cpu_values = [m["cpu_percent"] for m in metrics if m["cpu_percent"] is not None]
        memory_values = [m["memory_percent"] for m in metrics if m["memory_percent"] is not None]

        return {
            "average_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "peak_cpu_percent": max(cpu_values) if cpu_values else 0,
            "average_memory_percent": sum(memory_values) / len(memory_values) if memory_values else 0,
            "peak_memory_percent": max(memory_values) if memory_values else 0,
            "metrics_count": len(metrics),
        }

    def _generate_overall_recommendations(
        self, usage_stats: dict, performance_stats: dict, command_patterns: dict
    ) -> list[str]:
        """Generate overall recommendations."""
        recommendations = []

        # Usage-based recommendations
        if usage_stats.get("overall_statistics", {}).get("total_events", 0) < 10:
            recommendations.append("Consider using VersionTracker more regularly to get better insights.")

        # Performance-based recommendations
        if performance_stats.get("recommendations"):
            recommendations.extend(performance_stats["recommendations"])

        # Pattern-based recommendations
        common_patterns = command_patterns.get("common_patterns", [])
        if common_patterns and len(common_patterns) > 0:
            most_common = common_patterns[0][0]
            recommendations.append(f"Most common workflow: {most_common}. Consider creating shortcuts.")

        return recommendations

    def export_report_json(self, report: dict[str, Any], output_path: Path):
        """Export report as JSON."""
        output_path.write_text(json.dumps(report, indent=2, default=str))

    def export_report_markdown(self, report: dict[str, Any], output_path: Path):
        """Export report as Markdown."""
        lines = []
        lines.append("# VersionTracker Analytics Report")
        lines.append(f"**Period:** {report['report_period_days']} days")
        lines.append(f"**Generated:** {report['generated_at']}")
        lines.append("")

        # Usage Statistics
        usage_stats = report.get("usage_statistics", {})
        if usage_stats:
            lines.append("## Usage Statistics")
            overall = usage_stats.get("overall_statistics", {})
            lines.append(f"- Total Events: {overall.get('total_events', 0)}")
            lines.append(
                f"- Success Rate: {overall.get('successful_events', 0) / max(overall.get('total_events', 1), 1) * 100:.1f}%"
            )
            lines.append(f"- Average Duration: {overall.get('avg_duration', 0):.1f}ms")
            lines.append("")

        # Performance Insights
        perf_insights = report.get("performance_insights", {})
        if perf_insights:
            lines.append("## Performance Insights")
            slow_ops = perf_insights.get("slow_operations", [])
            if slow_ops:
                lines.append("### Slowest Operations")
                for op in slow_ops[:3]:
                    lines.append(f"- {op['operation']}: {op['avg_duration']:.1f}ms avg")
            lines.append("")

        # Recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            lines.append("## Recommendations")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        output_path.write_text("\n".join(lines))


class AnalyticsEngine:
    """Main analytics engine coordinating all analytics components."""

    def __init__(self, enable_analytics: bool = True):
        """Initialize analytics engine."""
        self.enabled = enable_analytics

        if self.enabled:
            self.event_logger = EventLogger()
            self.metrics_collector = MetricsCollector()
            self.usage_tracker = UsageTracker(self.event_logger)
            self.performance_monitor = PerformanceMonitor(self.event_logger)
            self.report_generator = AnalyticsReport(self.event_logger)

            # Start background metrics collection
            self._start_metrics_collection()
        else:
            logger.info("Analytics disabled")

    def _start_metrics_collection(self):
        """Start background system metrics collection."""

        def collect_metrics():
            while self.enabled:
                try:
                    metrics = self.metrics_collector.collect_system_metrics()
                    self.event_logger.log_system_metrics(metrics)
                except Exception as e:
                    logger.warning(f"Failed to collect system metrics: {e}")

                time.sleep(60)  # Collect every minute

        thread = threading.Thread(target=collect_metrics, daemon=True)
        thread.start()

    def track_command_execution(self, command: str, metadata: dict[str, Any] | None = None):
        """Context manager for tracking command execution."""
        if not self.enabled:
            return self._dummy_context()

        return self.usage_tracker.track_operation(command, metadata)

    def monitor_performance(self, operation: str, input_size: int = 0, metadata: dict[str, Any] | None = None):
        """Context manager for monitoring operation performance."""
        if not self.enabled:
            return self._dummy_context()

        return self.performance_monitor.monitor_operation(operation, input_size, metadata)

    @contextmanager
    def _dummy_context(self):
        """Dummy context manager when analytics is disabled."""
        yield {}

    def generate_report(self, days: int = 7, output_format: str = "dict") -> dict[str, Any] | str:
        """Generate analytics report."""
        if not self.enabled:
            return {"error": "Analytics disabled"}

        report = self.report_generator.generate_summary_report(days)

        if output_format == "json":
            return json.dumps(report, indent=2, default=str)
        elif output_format == "markdown":
            # Generate markdown from report dict
            return self._dict_to_markdown(report)
        else:
            return report

    def _dict_to_markdown(self, data: dict[str, Any], level: int = 1) -> str:
        """Convert dictionary to markdown format."""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{'#' * level} {key.replace('_', ' ').title()}")
                lines.append(self._dict_to_markdown(value, level + 1))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                lines.append(f"{'#' * level} {key.replace('_', ' ').title()}")
                for item in value[:5]:  # Limit to first 5 items
                    lines.append(f"- {item}")
            else:
                lines.append(f"**{key.replace('_', ' ').title()}:** {value}")
        return "\n".join(lines)

    def shutdown(self):
        """Shutdown analytics engine and flush pending data."""
        if self.enabled:
            self.enabled = False
            self.event_logger.flush()
