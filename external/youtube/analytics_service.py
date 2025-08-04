import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()

async def get_youtube_analytics_data(access_token: str, video_id: str) -> dict:
    url = (
        "https://youtubeanalytics.googleapis.com/v2/reports"
        "?ids=channel==MINE"
        "&startDate=2025-07-01"
        "&endDate=2025-07-27"
        "&metrics=audienceWatchRatio,relativeRetentionPerformance"
        "&dimensions=elapsedVideoTimeRatio"
        f"&filters=video=={video_id}"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch data: {response.text}"
        )

    return response.json()


def find_max_drop_time(analytics_rows, video_length_sec=60):
        # 종료 구간 제외 (예: elapsedRatio >= 0.95)
    filtered_rows = [row for row in analytics_rows if row[0] < 0.95]

    max_drop = 0
    drop_point = 0.0

    for i in range(1, len(filtered_rows)):
        prev_ratio = filtered_rows[i - 1][1]  # audienceWatchRatio
        curr_ratio = filtered_rows[i][1]
        drop = prev_ratio - curr_ratio

        if drop > max_drop:
            max_drop = drop
            drop_point = filtered_rows[i][0]  # elapsedVideoTimeRatio

    return drop_point
