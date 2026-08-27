# 2026-08-27-lift-ireland-k12-baml-dlt-cocoindex-v1

        > Lift cianfhoghlaim Ireland K-12 + LC BAML + DLT + CocoIndex (Primary + Secondary)

        ## Why

        The canonical Irish K-12 + LC pipeline lives in cianfhoghlaim. It is the substrate for gemini_hackathon's editorial canvas.

        ## What changes

        Lifted 4 stage BAML files (aistear, primary, junior_cycle, senior_cycle) into baml_extracts_education/stages/. Lifted 10 DLT source files (primary, junior_cycle, leaving_cert + 6 per-subject ncca_*.py) into dlt_pipelines/ireland/. Lifted 5 CocoIndex embedding files into cocoindex_flows/ireland/.

        ## Acceptance
        - All DLT modules import cleanly (the bare dlt_sources imports were stripped)
- CocoIndex shared_lifespan exports work
- 4 stage BAML files validate.