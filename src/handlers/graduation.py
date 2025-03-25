from handlers.base import RequestHandler, reqenv, Errors
from services.api import get_all_semester_info, get_subject_term_scores


class GraduationCreditsHandler(RequestHandler):
    async def _get_current_seme_credits(self, std_seme_id):
        """計算指定學期的選修和必修學分"""
        err, subject_scores = await get_subject_term_scores(self.session.session_id, std_seme_id)
        if err == Errors.RemoteServer:
            return err, None

        elective_course_credit_in_last_seme = 0
        required_course_credit_in_last_seme = 0
        for subject in subject_scores:
            if subject["course_type"] == "校選":
                elective_course_credit_in_last_seme += int(subject["credits"])
            elif subject["course_type"] == "部必":
                required_course_credit_in_last_seme += int(subject["credits"])
        return Errors.Success, {
            "elective_course": elective_course_credit_in_last_seme,
            "required_course": required_course_credit_in_last_seme,
        }

    @reqenv
    async def get(self):
        """處理 GET 請求，從學期成績中計算學分並判斷是否畢業"""
        if self.session is None:
            await self.render("goto-login.html")
            return

        session_id = self.session.session_id

        # 獲取所有學期資訊
        err, std_seme_view = await get_all_semester_info(session_id, self.session.student_id)
        if err == Errors.RemoteServer:
            await self.render_remote_server_err()
            return

        # 初始化學分計數器
        total_credits = 0
        required_credits = 0
        elective_credits = 0

        # 遍歷所有學期，累計學分
        for std in std_seme_view:
            std_seme_id = std["stdSemeId"]
            err, subject_scores = await get_subject_term_scores(session_id, std_seme_id)
            if err == Errors.RemoteServer:
                await self.render_remote_server_err()
                return

            for subject in subject_scores:
                if subject["pass"]:  # 僅計算通過的科目
                    credits = int(subject["credits"])
                    total_credits += credits
                    if subject["course_type"] == "部必":
                        required_credits += credits
                    elif subject["course_type"] == "校選":
                        elective_credits += credits

        # 假設的畢業要求（可根據實際需求調整）
        required_total_credits = 150
        required_required_credits = 100
        required_elective_credits = 50

        # 判斷是否畢業
        is_graduated = (
            total_credits >= required_total_credits and
            required_credits >= required_required_credits and
            elective_credits >= required_elective_credits
        )

        # 獲取最新學期的學分情況（用於顯示）
        latest_std_seme_id = std_seme_view[-1]["stdSemeId"] if std_seme_view else None
        credits_in_current_seme = None
        if latest_std_seme_id:
            err, credits_in_current_seme = await self._get_current_seme_credits(latest_std_seme_id)
            if err == Errors.RemoteServer:
                await self.render_remote_server_err()
                return

        # 準備渲染數據
        credits_info = {
            "total_credits": total_credits,
            "required_credits": required_credits,
            "elective_credits": elective_credits,
            "is_graduated": is_graduated,
        }

        # 渲染模板
        await self.render("graduation-credit.html", 
                         credits_info=credits_info, 
                         credits_in_current_seme=credits_in_current_seme)