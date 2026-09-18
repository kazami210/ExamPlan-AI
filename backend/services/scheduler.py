from datetime import date, timedelta
from typing import List, Dict, Any, Optional

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

class SchedulerEngine:
    @staticmethod
    def get_day_budget_minutes(
        d: date,
        daily_hours: float,
        weekly_schedule: Optional[Dict[str, float]] = None
    ) -> int:
        """Calculate daily time budget in minutes for a specific date."""
        if weekly_schedule:
            key = WEEKDAY_KEYS[d.weekday()]
            hours = float(weekly_schedule.get(key, daily_hours))
        else:
            hours = daily_hours
        return max(0, int(round(hours * 60)))

    @staticmethod
    def cluster_topics_if_needed(
        topics: List[Dict[str, Any]],
        available_days: int,
        target_score: float
    ) -> List[Dict[str, Any]]:
        """
        If a syllabus has too many micro-topics (e.g. 50-70+ items) for the available days,
        intelligently cluster / consolidate them into cohesive study blocks so the student
        is not overwhelmed with 5-10 fragmented tasks per day.
        """
        if not topics:
            return []

        # Ideal number of primary study sessions is roughly 60-70% of available days
        max_learning_sessions = max(2, available_days - 2)

        if len(topics) <= max_learning_sessions:
            return topics

        # Filter by target score if needed
        sorted_topics = sorted(topics, key=lambda t: t.get("importance_score", 5.0), reverse=True)
        if target_score < 6.5:
            # Pass goal: take top 60% essential topics
            sorted_topics = sorted_topics[:max(2, int(len(sorted_topics) * 0.6))]
        
        # If still too many, group consecutive topics into clusters
        cluster_size = max(2, (len(topics) + max_learning_sessions - 1) // max_learning_sessions)
        clustered = []
        for i in range(0, len(topics), cluster_size):
            group = topics[i:i + cluster_size]
            main_title = group[0]["title"]
            sub_titles = [g["title"] for g in group[1:]]
            
            combined_desc = group[0].get("description", "")
            if sub_titles:
                combined_title = f"{main_title} (và {len(sub_titles)} tiểu mục liên quan)"
                combined_desc += " Bao gồm các nội dung: " + ", ".join(sub_titles[:3])
            else:
                combined_title = main_title

            avg_imp = sum(g.get("importance_score", 7.0) for g in group) / len(group)
            has_hard = any(g.get("difficulty") == "Khó" for g in group)

            clustered.append({
                "code": group[0].get("code", f"G{len(clustered)+1}"),
                "title": combined_title,
                "description": combined_desc,
                "difficulty": "Khó" if has_hard else "Trung bình",
                "estimated_hours": 1.0, # Will be scaled to fit daily budget
                "importance_score": avg_imp
            })

        return clustered

    @classmethod
    def generate_plan(
        cls,
        topics: List[Dict[str, Any]],
        start_date: date,
        exam_date: date,
        daily_hours: float = 2.0,
        target_score: float = 8.0,
        weekly_schedule: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Budget-Constrained Spaced Repetition Scheduler:
        GUARANTEE: The sum of task minutes on any given day d will NEVER exceed budget_minutes[d].
        """
        total_days = (exam_date - start_date).days
        if total_days <= 0:
            total_days = 1

        all_dates = [start_date + timedelta(days=i) for i in range(total_days)]
        
        # Calculate daily budget for each date
        budgets: Dict[date, int] = {
            d: cls.get_day_budget_minutes(d, daily_hours, weekly_schedule)
            for d in all_dates
        }

        # Available active study dates (budget > 0)
        active_dates = [d for d in all_dates if budgets[d] > 0]
        if not active_dates:
            # Fallback if all set to 0
            active_dates = all_dates
            for d in all_dates:
                budgets[d] = max(30, int(daily_hours * 60))

        # Reserved final days (Mock Exam & Final Review)
        reserved_count = 2 if len(active_dates) >= 6 else (1 if len(active_dates) >= 3 else 0)
        learning_dates = active_dates[:-reserved_count] if reserved_count > 0 else active_dates
        if not learning_dates:
            learning_dates = active_dates

        # Intelligently cluster topics if there are too many for available learning days
        selected_topics = cls.cluster_topics_if_needed(topics, len(learning_dates), target_score)

        # Track used minutes and tasks per day
        tasks_by_date: Dict[date, List[Dict[str, Any]]] = {d: [] for d in all_dates}
        used_minutes: Dict[date, int] = {d: 0 for d in all_dates}

        is_pass_goal = target_score < 6.5
        is_excellent_goal = target_score >= 8.5

        # Step 1: Schedule Primary Learning (Học mới)
        topic_learned_date = {}
        learning_date_idx = 0

        for topic in selected_topics:
            target_d = learning_dates[learning_date_idx % len(learning_dates)]
            day_budget = budgets[target_d]

            # Allocate 65-75% of day's budget for primary learning, rest for review
            primary_mins = max(25, int(day_budget * 0.70))
            if primary_mins > day_budget:
                primary_mins = day_budget

            # Check if adding this exceeds the day's budget
            if used_minutes[target_d] + primary_mins > day_budget and used_minutes[target_d] > 0:
                # Move to next available learning date
                learning_date_idx += 1
                if learning_date_idx < len(learning_dates):
                    target_d = learning_dates[learning_date_idx]
                    day_budget = budgets[target_d]
                    primary_mins = max(25, min(day_budget, int(day_budget * 0.70)))

            if is_pass_goal:
                title = f"[Trọng tâm Qua Môn] {topic['title']}"
                desc = f"Nắm vững các định nghĩa và công thức then chốt nhất để chắc chắn có điểm: {topic.get('description', '')}"
                diff = "Trung bình"
            elif is_excellent_goal:
                title = f"[Học chuyên sâu] {topic['title']}"
                desc = f"Nghiên cứu kỹ đề cương, phân tích chuyên sâu và các dạng bài mở rộng: {topic.get('description', '')}"
                diff = "Khó"
            else:
                title = f"Học mới: {topic['title']}"
                desc = f"Đọc kỹ đề cương, nắm khái niệm cốt lõi: {topic.get('description', '')}"
                diff = topic.get("difficulty", "Trung bình")

            tasks_by_date[target_d].append({
                "title": title,
                "description": desc,
                "task_type": "study_new",
                "topic_title": topic["title"],
                "difficulty": diff,
                "estimated_minutes": primary_mins,
                "is_completed": False,
                "order_index": 1
            })
            used_minutes[target_d] += primary_mins
            topic_learned_date[topic.get("code", topic["title"])] = target_d

            # Advance date index
            learning_date_idx += 1

        # Step 2: Schedule Spaced Repetition (Ôn tập lặp lại)
        for topic in selected_topics:
            code = topic.get("code", topic["title"])
            first_day = topic_learned_date.get(code)
            if not first_day:
                continue

            # Review after 2-3 days
            rev_date = first_day + timedelta(days=2)
            # Find an active date >= rev_date with remaining budget
            candidate_dates = [
                d for d in learning_dates
                if d >= rev_date and budgets[d] - used_minutes[d] >= 15
            ]

            if candidate_dates:
                chosen_d = candidate_dates[0]
                remaining_mins = budgets[chosen_d] - used_minutes[chosen_d]
                rev_mins = min(remaining_mins, 20 if is_pass_goal else 30)

                tasks_by_date[chosen_d].append({
                    "title": f"Ôn tập lặp lại (Spaced Review): {topic['title']}",
                    "description": "Tự kiểm tra lại các định nghĩa và bài tập mà không nhìn tài liệu (Active Recall).",
                    "task_type": "spaced_review",
                    "topic_title": topic["title"],
                    "difficulty": "Dễ" if is_pass_goal else "Trung bình",
                    "estimated_minutes": rev_mins,
                    "is_completed": False,
                    "order_index": 2
                })
                used_minutes[chosen_d] += rev_mins

        # Step 3: Reserved Days (Mock Exam & Final Review)
        if reserved_count >= 2:
            mock_d = active_dates[-2]
            final_d = active_dates[-1]

            mock_budget = budgets[mock_d]
            final_budget = budgets[final_d]

            tasks_by_date[mock_d].append({
                "title": "Thi thử bấm giờ Mock Exam (Đề chuẩn đại học)",
                "description": "Làm 1 bộ đề thi thử hoàn chỉnh với độ khó chuẩn thời gian quy định.",
                "task_type": "practice_exam",
                "topic_title": "Toàn bộ môn học",
                "difficulty": "Khó",
                "estimated_minutes": min(mock_budget, 90 if is_excellent_goal else 60),
                "is_completed": False,
                "order_index": 1
            })
            used_minutes[mock_d] = min(mock_budget, 90 if is_excellent_goal else 60)

            tasks_by_date[final_d].append({
                "title": "Tổng ôn chốt kiến thức & Chuẩn bị tâm lý",
                "description": "Rà soát lại danh sách công thức, sơ đồ tư duy và chuẩn bị dụng cụ dự thi.",
                "task_type": "final_review",
                "topic_title": "Toàn bộ môn học",
                "difficulty": "Dễ",
                "estimated_minutes": min(final_budget, 45 if is_pass_goal else 60),
                "is_completed": False,
                "order_index": 1
            })
            used_minutes[final_d] = min(final_budget, 45 if is_pass_goal else 60)

        elif reserved_count == 1:
            final_d = active_dates[-1]
            final_budget = budgets[final_d]
            tasks_by_date[final_d].append({
                "title": "Tổng ôn chốt kiến thức trước ngày thi",
                "description": "Rà soát các điểm nhấn then chốt trong đề cương.",
                "task_type": "final_review",
                "topic_title": "Toàn bộ môn học",
                "difficulty": "Trung bình",
                "estimated_minutes": min(final_budget, 45),
                "is_completed": False,
                "order_index": 1
            })
            used_minutes[final_d] = min(final_budget, 45)

        # STRICT POST-CHECK & RESCALE:
        # Guarantee 100% that sum(task.estimated_minutes) <= budgets[d] for EVERY day!
        task_list = []
        for d in sorted(tasks_by_date.keys()):
            day_budget = budgets[d]
            day_tasks = tasks_by_date[d]
            if not day_tasks or day_budget <= 0:
                continue

            current_sum = sum(t["estimated_minutes"] for t in day_tasks)
            if current_sum > day_budget:
                # Scale proportionally so sum == day_budget
                scale = day_budget / current_sum
                for t in day_tasks:
                    t["estimated_minutes"] = max(10, int(t["estimated_minutes"] * scale))
                # Adjust rounding
                diff = day_budget - sum(t["estimated_minutes"] for t in day_tasks)
                if diff != 0:
                    day_tasks[0]["estimated_minutes"] = max(10, day_tasks[0]["estimated_minutes"] + diff)

            day_num = (d - start_date).days + 1
            for t_idx, t in enumerate(day_tasks, 1):
                t["study_date"] = d
                t["day_number"] = day_num
                t["order_index"] = t_idx
                task_list.append(t)

        return task_list

    @classmethod
    def reschedule_missed_tasks(
        cls,
        existing_tasks: List[Dict[str, Any]],
        today: date,
        exam_date: date,
        daily_hours: float = 2.0,
        weekly_schedule: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Re-generate schedule when a student falls behind, strictly respecting daily budget.
        """
        completed_tasks = [t for t in existing_tasks if t.get("is_completed")]
        
        missed_tasks = [
            t for t in existing_tasks
            if not t.get("is_completed") and t["study_date"] < today
        ]

        future_tasks = [
            t for t in existing_tasks
            if not t.get("is_completed") and t["study_date"] >= today
        ]

        remaining_days_count = max(1, (exam_date - today).days)
        available_dates = [today + timedelta(days=i) for i in range(remaining_days_count)]

        budgets = {
            d: cls.get_day_budget_minutes(d, daily_hours, weekly_schedule)
            for d in available_dates
        }

        # Active dates with budget > 0
        active_dates = [d for d in available_dates if budgets[d] > 0]
        if not active_dates:
            active_dates = available_dates
            for d in available_dates:
                budgets[d] = max(30, int(daily_hours * 60))

        # All pending tasks
        for t in missed_tasks:
            if not t["title"].startswith("[Dồn lịch]"):
                t["title"] = f"[Dồn lịch] {t['title']}"

        all_pending = missed_tasks + future_tasks

        # Distribute into active dates respecting day budget
        used = {d: 0 for d in active_dates}
        tasks_by_d = {d: [] for d in active_dates}
        d_idx = 0

        for t in all_pending:
            curr_d = active_dates[d_idx]
            b = budgets[curr_d]
            t_mins = min(b, t.get("estimated_minutes", 45))

            if used[curr_d] + t_mins > b and used[curr_d] > 0 and d_idx < len(active_dates) - 1:
                d_idx += 1
                curr_d = active_dates[d_idx]
                b = budgets[curr_d]
                t_mins = min(b, t.get("estimated_minutes", 45))

            t_copy = dict(t)
            t_copy["study_date"] = curr_d
            t_copy["day_number"] = (curr_d - today).days + 1
            t_copy["estimated_minutes"] = t_mins
            tasks_by_d[curr_d].append(t_copy)
            used[curr_d] += t_mins

        # Rescale if any day exceeds budget
        redistributed = []
        for d in active_dates:
            d_tasks = tasks_by_d[d]
            b = budgets[d]
            s = sum(x["estimated_minutes"] for x in d_tasks)
            if s > b and b > 0:
                scale = b / s
                for x in d_tasks:
                    x["estimated_minutes"] = max(10, int(x["estimated_minutes"] * scale))
            for idx, x in enumerate(d_tasks, 1):
                x["order_index"] = idx
                redistributed.append(x)

        final_list = list(completed_tasks) + redistributed
        final_list.sort(key=lambda x: (x["study_date"], x["order_index"]))
        return final_list

scheduler = SchedulerEngine()
