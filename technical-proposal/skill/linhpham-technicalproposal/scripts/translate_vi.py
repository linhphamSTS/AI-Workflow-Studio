# -*- coding: utf-8 -*-
"""Vietnamese pass for a proposal whose language was set to `vi` at the Phase 3 gate.

The content agents write the generated sections in Vietnamese already; what is still English
after build_docx is the template's own verbatim prose (development management, environments,
testing, UAT, the CASE STUDY frame), the headings, the generated table headers, the cover and
the page header. This pass translates exactly those, keeping English technical keywords
(Sprint, CI/CD, Production, User Acceptance Testing ...) untranslated.

Runs after a PASSING format review (two review checks read English phrases) and before
refresh_toc.py. `finalize.py` runs the whole order.

Usage:
  python translate_vi.py --docx <proposal.docx> --client "<client name>" [--report]
      --report only lists the English that would remain, and changes nothing.
Exit code 1 when English prose remains outside the dictionary, so a new template paragraph
cannot ship untranslated without anyone noticing.
"""
import argparse
import re
import sys
from docx import Document

_ap = argparse.ArgumentParser()
_ap.add_argument("--docx", required=True)
_ap.add_argument("--client", required=True, help="client name as written in the proposal")
_ap.add_argument("--report", action="store_true")
_args = _ap.parse_args()
DOCX = _args.docx
CLIENT = _args.client
REPORT_ONLY = _args.report
HEADER_CHARS = 42   # the page-header cell holds about 42 characters per line

# ---------------------------------------------------------------- headings
HEADINGS = {
    "Technical Proposal - High Level": "Đề xuất Kỹ thuật - High Level",
    "Content": "Mục lục",
    "INTRODUCTION": "GIỚI THIỆU",
    "Executive Summary": "Tóm tắt tổng quan",
    "Problems & Solutions": "Vấn đề và Giải pháp",
    "Purpose": "Mục đích",
    "PROPOSED TECHNOLOGY": "CÔNG NGHỆ ĐỀ XUẤT",
    "System Overview": "Tổng quan hệ thống",
    "SECURITY & DATA PROTECTION": "BẢO MẬT VÀ BẢO VỆ DỮ LIỆU",
    "PROPOSED DEVELOPMENT MANAGEMENT": "QUY TRÌNH QUẢN LÝ PHÁT TRIỂN",
    "Management Methodology (Optional)": "Phương pháp quản lý (Scrum)",
    "Development Flow": "Quy trình phát triển",
    "Branch Model": "Mô hình branch",
    "Development Environment": "Môi trường phát triển",
    "Quality Assurance": "Đảm bảo chất lượng",
    "Testing Workflow": "Luồng kiểm thử",
    "Testing Scope": "Phạm vi kiểm thử",
    "Testing Process": "Quy trình kiểm thử",
    "PROJECT TEAM": "ĐỘI NGŨ DỰ ÁN",
    "Engagement Model": "Mô hình hợp tác",
    "DELIVERY PLAN & GOVERNANCE": "KẾ HOẠCH TRIỂN KHAI VÀ QUẢN TRỊ",
    "Delivery Roadmap": "Lộ trình triển khai",
    "SUPPORT & SERVICE LEVELS": "HỖ TRỢ VÀ CAM KẾT DỊCH VỤ",
    "Service Level Targets": "Mục tiêu mức dịch vụ (SLA)",
    "ASSUMPTIONS, DEPENDENCIES & RISKS": "GIẢ ĐỊNH, PHỤ THUỘC VÀ RỦI RO",
    "Assumptions & Dependencies": "Giả định và Phụ thuộc",
    "Key Risks & Mitigations": "Rủi ro chính và Giảm thiểu",
    "SUMMARY": "TỔNG KẾT",
    "Mobile App Strategy": "Chiến lược mobile app",
    # optional sections (Phase 3 gate)
    "Team Structure": "Cơ cấu đội ngũ",
    "Roles & Responsibilities": "Vai trò và trách nhiệm",
    "Milestones & Acceptance": "Mốc bàn giao và nghiệm thu",
    "Support Model": "Mô hình hỗ trợ",
    "References": "Khách hàng tham chiếu",
    "Contractual Exceptions": "Ngoại lệ hợp đồng",
    "Phase 2 Scope & Triggers": "Phạm vi Giai đoạn 2 và điều kiện kích hoạt",
    # kept in English on purpose (technical keywords): Technology Stack, Back-end,
    # Front-end, Database, Server & Hosting, Data, AI, CASE STUDY, User Acceptance
    # Testing, 2.1.1 System Context, 4.2.1 CI / CD Pipeline, diagram subheadings.
}

# typed-number headings: translate the tail, keep the number
NUMBERED_HEADINGS = {
    "Testing Workflow": "Luồng kiểm thử",
    "Testing Scope": "Phạm vi kiểm thử",
    "Testing Process": "Quy trình kiểm thử",
}

# ---------------------------------------------------------------- body prose
# key = normalised English text (glyphs/tabs stripped, whitespace collapsed)
def norm(s):
    s = s.replace("●", " ").replace("○", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", s).strip()

BODY = {
# --- Management Methodology (Scrum) ---
"Sprint length: 2 week sprint":
 "Sprint length: sprint 2 tuần",
"Scrum role:":
 "Vai trò Scrum:",
"Product Owner (Client Project Manager)":
 "Product Owner (Quản lý dự án phía khách hàng)",
"Scrum Master (Service Provider Project Manager)":
 "Scrum Master (Quản lý dự án phía nhà cung cấp)",
"Development Team":
 "Development Team (đội phát triển)",
"Tester":
 "Tester (kiểm thử)",
"Project Roadmap:":
 "Project Roadmap:",
"Product Owner, Scrum Master to define the project roadmap and the target for each phase.":
 "Product Owner và Scrum Master xác định lộ trình dự án và mục tiêu cho từng giai đoạn.",
"Product Backlog:":
 "Product Backlog:",
"Scrum master, Product Owner to get raw requirements from Client then transfer them to User Story.":
 "Scrum Master và Product Owner tiếp nhận yêu cầu thô từ khách hàng rồi chuyển thành User Story.",
"Release Grooming:":
 "Release Grooming:",
"Scrum Master, Development Team to breakdown User Story to Epic and Task.":
 "Scrum Master và Development Team phân rã User Story thành Epic và Task.",
"Following the project roadmap, first define the sprint goal of this iteration, then select a list of user stories / epic / tasks to form the Sprint Backlog for the coming sprint which could fulfill the sprint goal.":
 "Theo lộ trình dự án, trước hết xác định sprint goal của vòng lặp, sau đó chọn danh sách user story, epic, task để lập Sprint Backlog cho sprint sắp tới sao cho đạt được sprint goal.",
"Sprint Planning:":
 "Sprint Planning:",
"Scrum Master, Development Team to review the current tasks, then estimate (Story Point) and arrangements for the workload based on the Sprint Backlog list.":
 "Scrum Master và Development Team rà soát các task hiện có, ước lượng bằng Story Point và phân bổ khối lượng theo danh sách Sprint Backlog.",
"Story Point is a scale of 1-13: 1 is very easy, 13 is very difficult.":
 "Story Point theo thang 1 đến 13: 1 là rất dễ, 13 là rất khó.",
"Each sprint, the Development Team should allocate at least 15-20% for coding review and customer feedback/bugs.":
 "Mỗi sprint, Development Team dành tối thiểu 15 đến 20% cho code review và xử lý feedback, bug từ khách hàng.",
"All questions need to be asked in this state.":
 "Mọi câu hỏi cần được nêu ra ngay ở bước này.",
"Sprint Backlog:":
 "Sprint Backlog:",
"Will be completed by the Development Team.":
 "Do Development Team hoàn thành.",
"During development time, change requests or bugs may be added by the Product Owner. Scrum Master to review the sprint scope, discuss with the Development Team and extend the current sprint if needed.":
 "Trong quá trình phát triển, Product Owner có thể bổ sung change request hoặc bug. Scrum Master rà soát phạm vi sprint, trao đổi với Development Team và gia hạn sprint hiện tại nếu cần.",
"Daily Standup:":
 "Daily Standup:",
"Within the Sprint, a Daily Scrum Meeting is required and each of the meetings is time-boxed in about 15 minutes.":
 "Trong sprint, họp Daily Scrum là bắt buộc, mỗi buổi gói gọn khoảng 15 phút.",
"Everyone needs to interact face-to-face with all members to share what they did yesterday and commit to what they want to achieve today. Questions about obstacles or unresolved issues could be raised also.":
 "Mọi thành viên trao đổi trực tiếp: chia sẻ việc đã làm hôm qua, cam kết việc sẽ đạt hôm nay, và nêu các vướng mắc hoặc vấn đề chưa xử lý xong.",
"Sprint Review:":
 "Sprint Review:",
"When all tickets in Sprint Backlog are completed, Scrum Master conducts a Sprint Review Meeting. The product owner and the customer must participate.":
 "Khi toàn bộ ticket trong Sprint Backlog hoàn thành, Scrum Master tổ chức họp Sprint Review. Product Owner và khách hàng bắt buộc tham dự.",
"Every member of the Scrum Team will demonstrate to them the working software they have completed and this meeting is very important and must not be canceled.":
 "Từng thành viên Scrum Team demo phần mềm chạy được đã hoàn thành; đây là buổi họp rất quan trọng và không được hủy.",
"Sprint Retrospective:":
 "Sprint Retrospective:",
"Start at the end of each sprint. During the retrospective, the team self-identifies elements of the process that did or did not work during the sprint, along with potential solutions. Retrospectives typically last 90 minutes and are there to help us incorporate continuous improvement into the team culture and into Sprint cadence.":
 "Diễn ra cuối mỗi sprint: đội tự nhìn nhận điểm làm tốt, điểm chưa tốt trong quy trình và đề xuất cải thiện. Buổi retrospective thường kéo dài 90 phút, giúp đưa cải tiến liên tục vào văn hóa đội và nhịp sprint.",
# --- CI/CD ---
"Every change reaches production through an automated pipeline that gates merges on quality and security and applies changes via a GitOps controller. The same pipeline produces the artifacts and manifests for all environments, so Dev, QA, Staging, UAT and Production are always reachable from a Git commit, fully auditable and reversible. Specific tooling (CI runner, security scanners, GitOps controller) is selected during detailed design and recorded in the low-level design document.":
 "Mọi thay đổi đi tới production qua một pipeline tự động: chặn merge bằng các cổng chất lượng và bảo mật, áp thay đổi qua GitOps controller. Cùng một pipeline sinh artifact và manifest cho mọi môi trường, nên Dev, QA, Staging, UAT và Production luôn truy được về một Git commit, audit được và đảo ngược được. Công cụ cụ thể (CI runner, công cụ quét bảo mật, GitOps controller) được chọn trong thiết kế chi tiết và ghi trong tài liệu low-level design.",
"1. Pull Request: requires at least two approvals (one from the Tech Lead for cross-cutting changes). No direct commits to main or develop.":
 "1. Pull Request: cần tối thiểu hai approval (một từ Tech Lead với thay đổi xuyên suốt). Không commit trực tiếp vào main hay develop.",
"2. CI quality gates: run on every PR, covering lint, unit tests with ≥ 80 % coverage on changed code, static analysis, SAST and dependency vulnerability scan. A failing gate blocks the merge.":
 "2. CI quality gates: chạy trên mọi PR, gồm lint, unit test với coverage tối thiểu 80% trên code thay đổi, static analysis, SAST và quét lỗ hổng dependency. Gạt nào fail thì chặn merge.",
"3. Container build, scan and push: a hardened distroless base image is built, scanned for vulnerabilities and signed before being pushed to the container registry with an immutable tag.":
 "3. Build, scan và push container: base image distroless được build, quét lỗ hổng và ký trước khi push lên container registry với tag bất biến.",
"4. GitOps controller: watches the Git desired-state and reconciles the cluster; the cluster is never modified by the CI step directly. This gives every deployment a Git commit as its identity.":
 "4. GitOps controller: theo dõi desired-state trong Git và reconcile hệ thống; bước CI không bao giờ sửa trực tiếp môi trường chạy. Nhờ đó mỗi lần deploy có định danh là một Git commit.",
"6. Failure path: any failed CI gate or production canary regression triggers an automatic rollback and notifies the developer via chat and a PR comment, keeping mean-time-to-recovery measured in minutes.":
 "6. Đường xử lý lỗi: bất kỳ CI gate nào fail hoặc canary trên production suy giảm sẽ kích hoạt rollback tự động và báo cho developer qua chat và PR comment, giữ thời gian phục hồi tính bằng phút.",
# --- Testing ---
"Saigon Technology recommends the adoption of the Basic Testing workflow across multiple testing levels, including unit testing, integration testing, system testing, and user acceptance testing. This approach entails the utilization of appropriate testing tools and frameworks tailored to each testing type, thereby ensuring the overall quality of the application.":
 "Saigon Technology khuyến nghị áp dụng luồng kiểm thử cơ bản ở nhiều cấp: unit testing, integration testing, system testing và user acceptance testing. Cách tiếp cận này dùng công cụ và framework kiểm thử phù hợp cho từng loại, bảo đảm chất lượng tổng thể của ứng dụng.",
"Testing to be involved within respective milestones of the development process are shall include:":
 "Kiểm thử gắn với từng mốc của quá trình phát triển gồm:",
"For each user story acceptance criteria are defined.":
 "Mỗi user story đều định nghĩa acceptance criteria.",
"For further quality assurance, system architecture documentation as well as source code inline documentation is mandatory.":
 "Để bảo đảm chất lượng sâu hơn, tài liệu kiến trúc hệ thống và comment trong source code là bắt buộc.",
"For the testing schedule, please allow two (2) days for client testing for each stage. These days shall be Saturday and Sunday so that feedback can be provided by Monday morning.":
 "Về lịch kiểm thử, mỗi giai đoạn xin dành 2 ngày cho khách hàng kiểm thử, ưu tiên thứ Bảy và Chủ nhật để có feedback vào sáng thứ Hai.",
"Test Planning: define a strategy, planning that include testing scope, objectives, resources, tools, techniques and schedule for the testing.":
 "Test Planning: xác định chiến lược và kế hoạch gồm phạm vi, mục tiêu, nguồn lực, công cụ, kỹ thuật và lịch kiểm thử.",
"Test Analysis: analyzes project’s requirements and specifications to identify testable features, objectives of the testing.":
 "Test Analysis: phân tích yêu cầu và đặc tả của dự án để xác định tính năng kiểm thử được và mục tiêu kiểm thử.",
"Test Design: design scenarios, high level cases, data, environment, and the techniques based on different expectations are analyzed.":
 "Test Design: thiết kế kịch bản, case mức cao, dữ liệu, môi trường và kỹ thuật dựa trên các kỳ vọng đã phân tích.",
"Test Implementation: develop test cases details, and test scripts (if any) based on the scenarios, high level cases.":
 "Test Implementation: viết test case chi tiết và test script (nếu có) dựa trên kịch bản và case mức cao.",
"Test Execution: execute tests based on the test cases detailed, test scripts by comparing the actual behaviors against the expectation. Defects, issues are also identified and logged for tracking during this phase.":
 "Test Execution: thực thi theo test case chi tiết và test script, so sánh hành vi thực tế với kỳ vọng; defect và issue được ghi nhận để theo dõi trong giai đoạn này.",
"Test Completion: generate final reports, summarize the testing activities, results and any remaining issues, then send to stake holders for release approval or send back to the development team for fixing.":
 "Test Completion: lập báo cáo cuối, tổng hợp hoạt động, kết quả và issue còn lại, gửi các bên liên quan phê duyệt release hoặc chuyển lại đội phát triển để sửa.",
# --- UAT ---
"Saigon Technology recognizes the importance of User Acceptance Testing (UAT) in ensuring the successful delivery of our project. Below are the guidelines for UAT within the scope of our collaboration:":
 "Saigon Technology hiểu rõ tầm quan trọng của User Acceptance Testing (UAT) đối với việc bàn giao thành công. Dưới đây là nguyên tắc UAT trong phạm vi hợp tác:",
"Client Responsibility and Timeline: The client is responsible for conducting UAT for each milestone or project. UAT should be completed within 14 days from the day Saigon Technology officially sends the UAT notification email to the client.":
 "Trách nhiệm và thời hạn của khách hàng: khách hàng thực hiện UAT cho từng milestone hoặc dự án. UAT cần hoàn thành trong 14 ngày kể từ ngày Saigon Technology gửi email thông báo UAT chính thức.",
"UAT Success Confirmation: Following the UAT period with no client feedback, Saigon Technology reserves the right to regard the UAT as successful. Upon successful UAT, Saigon Technology will proceed to raise the respective invoice.":
 "Xác nhận UAT thành công: hết thời hạn UAT mà không có feedback từ khách hàng, Saigon Technology có quyền xem UAT là thành công. Khi UAT thành công, Saigon Technology phát hành hóa đơn tương ứng.",
"Bug Resolution: Critical and high bugs identified during the UAT period will be addressed promptly by Saigon Technology within 3 weeks from the raised date. The resolution of medium and minor bugs will be carried out in a timely manner to maintain the flexibility of deliverables.":
 "Xử lý bug: bug mức critical và high phát hiện trong thời gian UAT được Saigon Technology xử lý trong 3 tuần kể từ ngày ghi nhận. Bug mức medium và minor được xử lý kịp thời để giữ tiến độ bàn giao linh hoạt.",
"Client Rejection: In the event of the client choosing to reject the deliverable in the UAT period, the client must provide the substantiated reasons for the rejection, along with validated evidence. Additionally, the determination of the fixed bug resolution time and the UAT period should be deliberated in accordance with the guidelines outlined in User Acceptance Testing.":
 "Từ chối nghiệm thu: nếu khách hàng từ chối deliverable trong thời gian UAT, khách hàng cần nêu lý do có căn cứ kèm bằng chứng đã kiểm chứng. Thời gian sửa bug và thời hạn UAT được xác định theo đúng nguyên tắc đã nêu trong phần User Acceptance Testing.",
# --- CASE STUDY frame ---
"We are pleased to present a relevant case study that demonstrates our ability to deliver a high-performance, multi-stakeholder B2B platform comparable to":
 "Chúng tôi xin giới thiệu một case study thể hiện năng lực xây dựng nền tảng B2B nhiều bên liên quan, hiệu năng cao, tương đồng với",
# --- Phase table (Development Flow) ---
"Analyze Task": "Phân tích task",
"Developer picks up a task from the Sprint backlog and start analyze the task:":
 "Developer nhận task từ Sprint Backlog và bắt đầu phân tích:",
"Read tickets and clarify with BA, PM/PC or Client all unclear requirements.":
 "Đọc ticket và làm rõ với BA, PM/PC hoặc khách hàng mọi yêu cầu chưa rõ.",
"Review current project source code (if any) to understand the current context.":
 "Xem source code hiện có của dự án (nếu có) để hiểu bối cảnh.",
"List out all possible test cases.":
 "Liệt kê các test case có thể có.",
"Design": "Thiết kế",
"Design solution for the task:":
 "Thiết kế giải pháp cho task:",
"Define class design, database design, class diagrams and sequence diagrams (if required).":
 "Xác định class design, database design, class diagram và sequence diagram (nếu cần).",
"Discuss with Back-end Dev Lead about this solution to finalize the design.":
 "Trao đổi với Back-end Dev Lead để chốt thiết kế.",
"Define a smaller task list to track progress.":
 "Chia task nhỏ hơn để theo dõi tiến độ.",
"Start Coding": "Bắt đầu code",
"Start coding based on agreed design.":
 "Code theo thiết kế đã thống nhất.",
"Unit Test": "Unit Test",
"Create unit tests if required.":
 "Viết unit test nếu được yêu cầu.",
"Execute unit tests and fix any defects found.":
 "Chạy unit test và sửa defect phát hiện được.",
"Note: The unit test is not in this scope of work.":
 "Ghi chú: unit test không thuộc phạm vi công việc này.",
"Pull Request": "Pull Request",
"Create a pull-request and resolve all conflicts to be reviewed by the Dev Lead and team members.":
 "Tạo pull request và xử lý hết conflict để Dev Lead và thành viên review.",
"Review & Merge Code": "Review và merge code",
"Review source code in the pull request based on the style guide or coding convention of the project (must create one for the project).":
 "Review source code trong pull request theo style guide hoặc coding convention của dự án (bắt buộc có cho dự án).",
"Comment on blocks of code having issues and suggest ideas to fix.":
 "Comment vào đoạn code có vấn đề và gợi ý cách sửa.",
"Taking note to share this as a lesson learned for other developers if necessary.":
 "Ghi chú để chia sẻ thành lesson learned cho developer khác khi cần.",
"Merge feature branch into branch DEV.":
 "Merge feature branch vào branch DEV.",
"Developer": "Developer",
"Leader/Tech Lead": "Leader/Tech Lead",
"Phase": "Giai đoạn",
"Description": "Mô tả",
"Person in-charge": "Người phụ trách",
# --- Branch table ---
"Branch": "Branch",
"Purpose": "Mục đích",
"Store the stable source code.": "Lưu source code ổn định.",
"To release to STA/DEMO and PROD.": "Để release lên STA/DEMO và PROD.",
"To fix a bug on PROD, the developer needs to create a new hotfix branch from PROD, fix the bug then release it to STA/DEMO to verify":
 "Để sửa bug trên PROD, developer tạo hotfix branch mới từ PROD, sửa xong release lên STA/DEMO để kiểm chứng",
"Store the latest source code.": "Lưu source code mới nhất.",
"To release to QA Environment.": "Để release lên môi trường QA.",
"To integrate and merge the feature code.": "Để tích hợp và merge code tính năng.",
"To fix a bug on QA Environment, the developer needs to create a new hotfix branch from DEV, fix the bug then release it to QA Environment again to verify.":
 "Để sửa bug trên môi trường QA, developer tạo hotfix branch mới từ DEV, sửa xong release lại lên QA để kiểm chứng.",
"Store the feature/hotfix source code.": "Lưu source code của feature/hotfix.",
"For feature, Developer to create a new feature branch with name DevName_TaskName_TaskID_Date when start developing any feature.":
 "Với feature, developer tạo feature branch tên DevName_TaskName_TaskID_Date khi bắt đầu làm.",
"For hotfix, the Developer creates a new hotfix branch with the name DevName_Hotfix_TaskID_Date when they start fixing any bug.":
 "Với hotfix, developer tạo hotfix branch tên DevName_Hotfix_TaskID_Date khi bắt đầu sửa bug.",
# --- Environment table ---
"Environment": "Môi trường",
"Local": "Local",
"An environment for developers to develop features, do self testing":
 "Môi trường để developer phát triển tính năng và tự kiểm thử",
"An environment for developers to integrate FE and BE code and self test full features. Developers can invite testers/product owners to review features to ask for early feedback.":
 "Môi trường để developer tích hợp code FE và BE, tự kiểm thử đầy đủ tính năng; có thể mời tester/Product Owner xem sớm để lấy feedback.",
"A testing environment for tester/product owner to do integration testing and verify all issues before demo.":
 "Môi trường kiểm thử để tester/Product Owner chạy integration testing và kiểm chứng issue trước khi demo.",
"A full copy of production for product owner to demo application to client or do full workflow testing before rollout the new version to production.":
 "Bản sao đầy đủ của production để Product Owner demo cho khách hàng hoặc kiểm thử trọn luồng trước khi rollout phiên bản mới.",
"Before releasing any version, a full backup of production needs to be prepared. After release, the smoke testing is required. Only some people in the white list IP can access the system and do the smoke testing.":
 "Trước khi release phiên bản bất kỳ cần backup đầy đủ production. Sau release bắt buộc smoke testing; chỉ người trong danh sách IP được phép truy cập để smoke testing.",
"Development": "Development",
"Testing/Staging": "Testing/Staging",
"UAT/Pre-Production": "UAT/Pre-Production",
"Live/Production": "Live/Production",
# --- Testing responsibility table ---
"Testing": "Hạng mục kiểm thử",
"Responsibility": "Trách nhiệm",
"Functionality Testing": "Functionality Testing",
"UI Testing": "UI Testing",
"Integration Testing": "Integration Testing",
"Regression Testing": "Regression Testing",
"User Acceptance Testing (test cases as per user stories)":
 "User Acceptance Testing (test case theo user story)",
"QC": "QC",
"Client": "Khách hàng",
# --- generated table headers ---
"Technology": "Công nghệ",
"Advantages": "Ưu điểm",
"Role": "Vai trò",
"Accountability": "Trách nhiệm",
# --- cover labels ---
"ISSUED TO": "GỬI ĐẾN",
"ISSUED FROM": "ĐƠN VỊ PHÁT HÀNH",
}

CICD_STEP5_EN_PREFIX = "5. CD environments promoted in order"
CICD_STEP5_VI = ("5. Các môi trường CD promote theo thứ tự: DEV (tự động khi merge), QA "
                 "(integration và API contract test), Staging (load test hiệu năng và regression), UAT "
                 "(" + CLIENT + " nghiệm thu), Production (blue-green / canary, "
                 "rollback tự động khi suy giảm).")

def set_para_text(p, new_text):
    """Replace paragraph text, preserving the bold-label split when EN and VI share a ':' boundary."""
    runs = [r for r in p.runs]
    if not runs:
        return False
    # keep any leading glyph/tab prefix that survives in run 0
    m = re.match(r"^([●○]\s*|\t| )*", runs[0].text or "")
    # colon-split: if some run boundary ends exactly at a ':' and VI has a ':'
    if ":" in new_text:
        cum = ""
        for i, r in enumerate(runs[:-1]):
            cum += r.text or ""
            if cum.rstrip().endswith(":"):
                vi_label, vi_rest = new_text.split(":", 1)
                pre = re.match(r"^([●○]\s*|\t)*", runs[0].text or "").group(0)
                runs[0].text = pre + vi_label + ":"
                for j in range(1, i + 1):
                    runs[j].text = ""
                runs[i + 1].text = vi_rest
                for j in range(i + 2, len(runs)):
                    runs[j].text = ""
                return True
    pre = re.match(r"^([●○]\s*|\t)*", runs[0].text or "").group(0)
    runs[0].text = pre + new_text
    for r in runs[1:]:
        r.text = ""
    return True

def looks_english(t):
    words = re.findall(r"[a-zA-Z]+", t)
    if len(words) < 4:
        return False
    hits = sum(1 for w in ("the", "and", "for", "with", "from", "must", "will", "are", "is",
                           "to", "of", "be", "this", "that", "by", "on", "in")
               if re.search(r"\b%s\b" % w, t, re.I))
    return hits >= 3

def translate_paragraph(p, stats):
    t = p.text
    if not t.strip():
        return
    key = norm(t)
    if key in BODY:
        if not REPORT_ONLY:
            set_para_text(p, BODY[key])
        stats["hit"] += 1
        return
    if key.startswith(norm(CICD_STEP5_EN_PREFIX)):
        if not REPORT_ONLY:
            set_para_text(p, CICD_STEP5_VI)
        stats["hit"] += 1
        return
    # case-study frame: contains the filled title, match by prefix
    cs = "We are pleased to present a relevant case study"
    if key.startswith(cs):
        stats["case_study"].append(p)
        return
    if looks_english(t):
        stats["residual"].append(t[:130])

def translate_solution_labels(d, stats):
    """build_docx renders each P&S pair as '**Solution:** ...' - translate the bold label."""
    for p in d.paragraphs:
        for r in p.runs:
            if r.text and r.text.strip().startswith("Solution:"):
                if not REPORT_ONLY:
                    r.text = r.text.replace("Solution:", "Giải pháp:", 1)
                stats["hit"] += 1


def translate_headers_footers(d, stats):
    for sec in d.sections:
        for part in (sec.header, sec.footer, sec.first_page_header, sec.first_page_footer):
            if part is None:
                continue
            for p in part.paragraphs:
                for r in p.runs:
                    if not r.text:
                        continue
                    new = r.text
                    new = new.replace("Technical Proposal - High Level", "Đề xuất Kỹ thuật - High Level")
                    if new.strip().startswith("for ") or new.startswith("for "):
                        new = new.replace("for ", "cho ", 1)
                    if new != r.text:
                        if not REPORT_ONLY:
                            r.text = new
                        stats["hit"] += 1


def _vi_title_line(text):
    new = text.replace("Technical Proposal - High Level", "Đề xuất Kỹ thuật - High Level")
    if new.startswith("for "):
        new = "cho " + new[4:]
    return new


def _vi_header_line(text):
    # The header cell fits about 42 characters per line. A full project title wraps and leaves
    # the last word of the client name alone on a third line of every page, so the header
    # drops any parenthetical gloss the cover keeps. If it is still too long, the report says so.
    new = _vi_title_line(text)
    if len(new) > HEADER_CHARS:
        new = re.sub(r"\s*\([^)]*\)", "", new)
    return new


def translate_cover_and_header_tables(d, stats):
    """Cover title lines, the header table (python-docx header.paragraphs skips tables), and the
    ISSUED TO / FROM role labels. The template types 'Project Coordinator' twice in the FROM cell;
    the second copy is a template slip and is removed."""
    for p in d.paragraphs[:5]:
        for r in p.runs:
            if r.text and _vi_title_line(r.text) != r.text:
                if not REPORT_ONLY:
                    r.text = _vi_title_line(r.text)
                stats["hit"] += 1
    for sec in d.sections:
        for part in (sec.header, sec.first_page_header):
            for tb in part.tables:
                for row in tb.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            for r in p.runs:
                                if r.text and _vi_header_line(r.text) != r.text:
                                    if not REPORT_ONLY:
                                        r.text = _vi_header_line(r.text)
                                    stats["hit"] += 1
    roles = {"Project Sponsor": "Đầu mối dự án", "Project Coordinator": "Điều phối dự án"}
    for row in d.tables[0].rows:
        for cell in row.cells:
            seen = set()
            for p in list(cell.paragraphs):
                t = p.text.strip()
                if t in roles:
                    if t in seen and not REPORT_ONLY:
                        p._p.getparent().remove(p._p)
                        stats["hit"] += 1
                        continue
                    seen.add(t)
                    if not REPORT_ONLY:
                        set_para_text(p, roles[t])
                    stats["hit"] += 1


# Captions of the template's own pictures ("Figure N: <name>"). "Figure" becomes "Hình" in the
# table-cell pass; the name after it needs its own table, or the caption stays half English.
CAPTIONS = {
    "Agile Methodology": "Phương pháp Agile",
    "CI / CD Pipeline (GitOps Delivery)": "Quy trình CI / CD (GitOps)",
    "Branching Model": "Mô hình branch",
    "Development Workflow": "Luồng phát triển",
    "Basic Testing Workflow": "Luồng kiểm thử cơ bản",
    "Testing Process": "Quy trình kiểm thử",
}


def translate_captions(d, stats):
    def paras():
        yield from d.paragraphs
        for tb in d.tables:
            for row in tb.rows:
                for cell in row.cells:
                    yield from cell.paragraphs
    for p in paras():
        if not p.text.strip().startswith(("Figure", "Hình")):
            continue
        for r in p.runs:
            for en, vi in CAPTIONS.items():
                if r.text and en in r.text:
                    if not REPORT_ONLY:
                        r.text = r.text.replace(en, vi)
                    stats["hit"] += 1


def swap_template_pictures(d):
    """Replace the template's English process pictures with their Vietnamese versions.

    The pictures are matched by the hash of their bytes, so only an untouched template picture
    is swapped; templates/vi/ is built by make_vi_template_images.py. Returns the count."""
    import hashlib
    import json as _json
    from pathlib import Path
    vi_dir = Path(__file__).resolve().parent.parent / "templates" / "vi"
    index = vi_dir / "index.json"
    if not index.exists():
        return 0
    table = _json.loads(index.read_text(encoding="utf-8"))
    n = 0
    for rel in d.part.rels.values():
        if "image" not in rel.reltype or rel.is_external:
            continue
        part = rel.target_part
        key = hashlib.sha1(part.blob).hexdigest()[:12]
        if key in table:
            part._blob = (vi_dir / table[key]["file"]).read_bytes()
            n += 1
    return n


def main():
    d = Document(DOCX)
    stats = {"hit": 0, "residual": [], "case_study": [], "head": 0}
    if not REPORT_ONLY:
        print("template pictures swapped for Vietnamese versions:", swap_template_pictures(d))
    translate_captions(d, stats)
    translate_solution_labels(d, stats)
    translate_headers_footers(d, stats)
    translate_cover_and_header_tables(d, stats)

    # headings
    for p in d.paragraphs:
        st = (p.style.name or "").lower()
        if not st.startswith("heading"):
            continue
        t = p.text.strip()
        if t in HEADINGS:
            if not REPORT_ONLY:
                set_para_text(p, HEADINGS[t])
            stats["head"] += 1
            continue
        m = re.match(r"^(\d+(?:\.\d+)*\.?\s+)(.*)$", t)
        if m and m.group(2) in NUMBERED_HEADINGS:
            if not REPORT_ONLY:
                set_para_text(p, m.group(1) + NUMBERED_HEADINGS[m.group(2)])
            stats["head"] += 1

    # body paragraphs
    for p in d.paragraphs:
        st = (p.style.name or "").lower()
        if st.startswith("heading"):
            continue
        translate_paragraph(p, stats)

    # table cells (all tables, per-paragraph)
    for tb in d.tables:
        for row in tb.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if "Figure" in p.text and not REPORT_ONLY:
                        for r in p.runs:
                            if r.text and "Figure" in r.text:
                                r.text = r.text.replace("Figure", "Hình")
                                stats["hit"] += 1
                    translate_paragraph(p, stats)

    # cached TOC entries: any non-heading paragraph whose text starts with a known heading EN name
    toc_map = dict(HEADINGS)
    for p in d.paragraphs:
        st = (p.style.name or "").lower()
        if st.startswith("heading"):
            continue
        txt = p.text
        for en, vi in toc_map.items():
            if txt.strip().startswith(en) and ("\t" in txt or "PAGEREF" in p._p.xml):
                if not REPORT_ONLY:
                    for r in p.runs:
                        if r.text and en in r.text:
                            r.text = r.text.replace(en, vi)
                            stats["hit"] += 1
                break

    print("headings translated:", stats["head"])
    print("body/cell hits:", stats["hit"])
    print("case-study frame paragraphs found:", len(stats["case_study"]))
    long_headers = [r.text for sec in d.sections for part in (sec.header, sec.first_page_header)
                    for tb in part.tables for row in tb.rows for cell in row.cells
                    for p in cell.paragraphs for r in p.runs
                    if r.text and r.text.startswith("cho ") and len(r.text) > HEADER_CHARS]
    if long_headers:
        print("PAGE HEADER STILL TOO LONG (>%d chars, it will wrap): %s" % (HEADER_CHARS, long_headers))
    if stats["residual"]:
        print("RESIDUAL ENGLISH (%d):" % len(stats["residual"]))
        for r in stats["residual"]:
            print("  - " + r)
    if not REPORT_ONLY:
        d.save(DOCX)
        print("saved:", DOCX)
    if stats["residual"] or long_headers:
        print("Add each residual paragraph to BODY (or shorten the project title in the header), "
              "then re-run from the reviewed English backup.")
        sys.exit(1)

if __name__ == "__main__":
    main()
