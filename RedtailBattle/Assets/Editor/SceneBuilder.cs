#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.UI;
using TMPro;

/// <summary>
/// One-click scene builder.
/// Menu: Redtail ▶ Build Scene
/// </summary>
public static class SceneBuilder
{
    // ── Brand colours ──────────────────────────────────────────────────────────
    static readonly Color COL_ORANGE  = new Color(1.00f, 0.45f, 0.05f); // player
    static readonly Color COL_BLUE    = new Color(0.10f, 0.55f, 1.00f); // AI rival
    static readonly Color COL_GREEN   = new Color(0.22f, 0.55f, 0.22f); // arena grass
    static readonly Color COL_SKY     = new Color(0.50f, 0.80f, 0.50f); // background
    static readonly Color COL_DARK    = new Color(0.06f, 0.06f, 0.10f); // HUD bg
    static readonly Color COL_HP_POS  = new Color(0.20f, 0.90f, 0.30f); // HP green
    static readonly Color COL_HP_NEG  = new Color(0.80f, 0.15f, 0.15f); // HP red

    // ── Arena layout (world units) ─────────────────────────────────────────────
    const float ARENA_Y       = -1.5f;  // ground Y
    const float ARENA_HALF_W  =  4.0f;  // half-width
    const float ARENA_H       =  1.0f;  // platform height

    // ── Entry point ───────────────────────────────────────────────────────────

    [MenuItem("Redtail/Build Scene")]
    public static void BuildScene()
    {
        if (EditorApplication.isPlaying)
        {
            Debug.LogWarning("[SceneBuilder] Stop Play mode first, then run Redtail > Build Scene.");
            return;
        }

        // New untitled scene
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // ── Camera ────────────────────────────────────────────────────────────
        var camGO = new GameObject("Main Camera");
        camGO.tag = "MainCamera";
        var cam = camGO.AddComponent<Camera>();
        cam.orthographic     = true;
        cam.orthographicSize = 5f;
        cam.backgroundColor  = COL_SKY;
        cam.transform.position = new Vector3(0, 0, -10);
        camGO.AddComponent<AudioListener>();

        // ── Background ────────────────────────────────────────────────────────
        CreateBackground();

        // ── Arena platform ────────────────────────────────────────────────────
        CreatePlatform();

        // ── Fighters ──────────────────────────────────────────────────────────
        var player = CreateFighter("Player", new Vector3(-2.5f, ARENA_Y + 0.9f, 0), COL_ORANGE, true);
        var ai     = CreateFighter("AI",     new Vector3( 2.5f, ARENA_Y + 0.9f, 0), COL_BLUE,   false);

        // Make the fighters face each other initially
        var aiScale = ai.transform.localScale;
        aiScale.x = -Mathf.Abs(aiScale.x);
        ai.transform.localScale = aiScale;

        // ── GameManager ───────────────────────────────────────────────────────
        var gmGO = new GameObject("GameManager");
        gmGO.AddComponent<GameManager>();

        // ── Canvas / UI ───────────────────────────────────────────────────────
        BuildUI(player, ai);

        // Save
        string path = "Assets/Scenes/GameScene.unity";
        System.IO.Directory.CreateDirectory("Assets/Scenes");
        EditorSceneManager.SaveScene(scene, path);
        AssetDatabase.Refresh();

        Debug.Log("[SceneBuilder] Scene saved to " + path +
                  "\n▶  Press Play to start the game!" +
                  "\n   Controls: A/D or ←/→ to move, SPACE to punch, X/K to kick, ENTER to start.");
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    static void CreateBackground()
    {
        // Sky gradient via a simple quad
        var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
        go.name = "Background";
        go.transform.position   = new Vector3(0, 0, 5);
        go.transform.localScale = new Vector3(20, 12, 1);
        var rend = go.GetComponent<MeshRenderer>();
        var mat  = new Material(Shader.Find("Sprites/Default"));
        mat.color = COL_SKY;
        rend.sharedMaterial = mat;
        Object.DestroyImmediate(go.GetComponent<MeshCollider>());

        // Some simple decorative "bushes" as small circles
        for (int i = -3; i <= 3; i++)
        {
            if (Mathf.Abs(i) < 2) continue;
            var bush = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            bush.name = "Bush_" + i;
            bush.transform.position   = new Vector3(i * 1.3f, ARENA_Y + 0.2f, 1);
            bush.transform.localScale = Vector3.one * Random.Range(0.4f, 0.7f);
            var bm = new Material(Shader.Find("Sprites/Default"));
            bm.color = new Color(0.12f, 0.45f, 0.12f);
            bush.GetComponent<MeshRenderer>().sharedMaterial = bm;
            Object.DestroyImmediate(bush.GetComponent<SphereCollider>());
        }
    }

    static void CreatePlatform()
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = "Arena";
        go.transform.position   = new Vector3(0, ARENA_Y - ARENA_H * 0.5f, 1);
        go.transform.localScale = new Vector3(ARENA_HALF_W * 2, ARENA_H, 1);
        var mat = new Material(Shader.Find("Sprites/Default"));
        mat.color = COL_GREEN;
        go.GetComponent<MeshRenderer>().sharedMaterial = mat;
        Object.DestroyImmediate(go.GetComponent<BoxCollider>());
    }

    static GameObject CreateFighter(string tag, Vector3 pos, Color bodyColor, bool addPlayer)
    {
        var root = new GameObject(tag);
        root.tag = tag;
        root.transform.position = pos;

        // ── Body (rectangle) ──────────────────────────────────────────────────
        var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
        body.name = "Body";
        body.transform.SetParent(root.transform);
        body.transform.localPosition = Vector3.zero;
        body.transform.localScale    = new Vector3(0.55f, 0.9f, 0.2f);
        var bmat = new Material(Shader.Find("Sprites/Default"));
        bmat.color = bodyColor;
        var bRend = body.GetComponent<MeshRenderer>();
        bRend.sharedMaterial = bmat;
        Object.DestroyImmediate(body.GetComponent<BoxCollider>());

        // ── Helmet (darker circle on top) ─────────────────────────────────────
        var helm = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        helm.name = "Helmet";
        helm.transform.SetParent(root.transform);
        helm.transform.localPosition = new Vector3(0, 0.65f, 0);
        helm.transform.localScale    = Vector3.one * 0.5f;
        var hmat = new Material(Shader.Find("Sprites/Default"));
        hmat.color = bodyColor * 0.7f;
        helm.GetComponent<MeshRenderer>().sharedMaterial = hmat;
        Object.DestroyImmediate(helm.GetComponent<SphereCollider>());

        // ── Left arm ──────────────────────────────────────────────────────────
        var arm = GameObject.CreatePrimitive(PrimitiveType.Cube);
        arm.name = "ArmL";
        arm.transform.SetParent(root.transform);
        arm.transform.localPosition = new Vector3(-0.38f, 0.1f, 0);
        arm.transform.localScale    = new Vector3(0.2f, 0.5f, 0.2f);
        arm.GetComponent<MeshRenderer>().sharedMaterial = bmat;
        Object.DestroyImmediate(arm.GetComponent<BoxCollider>());

        // ── Right arm ─────────────────────────────────────────────────────────
        var arm2 = GameObject.CreatePrimitive(PrimitiveType.Cube);
        arm2.name = "ArmR";
        arm2.transform.SetParent(root.transform);
        arm2.transform.localPosition = new Vector3(0.38f, 0.1f, 0);
        arm2.transform.localScale    = new Vector3(0.2f, 0.5f, 0.2f);
        arm2.GetComponent<MeshRenderer>().sharedMaterial = bmat;
        Object.DestroyImmediate(arm2.GetComponent<BoxCollider>());

        // ── Fighter component ─────────────────────────────────────────────────
        var fighter = root.AddComponent<Fighter>();
        fighter.bodyRenderer   = bRend;
        fighter.helmetRenderer = helm.GetComponent<Renderer>();

        // ── Physics (Rigidbody2D already added by [RequireComponent] on Fighter)
        var rb = root.GetComponent<Rigidbody2D>();
        rb.gravityScale  = 0;
        rb.constraints   = RigidbodyConstraints2D.FreezeRotation;
        var col = root.AddComponent<BoxCollider2D>();
        col.size = new Vector2(0.6f, 1.0f);

        // ── Controller ────────────────────────────────────────────────────────
        if (addPlayer)
            root.AddComponent<PlayerController>();
        else
            root.AddComponent<AIController>();

        return root;
    }

    static void BuildUI(GameObject player, GameObject ai)
    {
        // ── Canvas ────────────────────────────────────────────────────────────
        var canvasGO = new GameObject("Canvas");
        var canvas   = canvasGO.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvasGO.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        canvasGO.GetComponent<CanvasScaler>().referenceResolution = new Vector2(390, 844);
        canvasGO.AddComponent<GraphicRaycaster>();

        // ── HUD panel ─────────────────────────────────────────────────────────
        var hud = CreatePanel(canvasGO, "HUD", new Vector2(0, 1), new Vector2(0, 1),
                              new Vector2(0, -80), new Vector2(390, 70));
        hud.GetComponent<Image>().color = new Color(0, 0, 0, 0.75f);

        // Player HP label
        CreateLabel(hud, "PlayerLabel", "YOU",
                    new Vector2(0, 0.5f), new Vector2(0, 0.5f),
                    new Vector2(50, 0), new Vector2(80, 30), COL_ORANGE, 14, TextAlignmentOptions.Left);

        // Player HP bar
        var playerBar = CreateHPBar(hud, "PlayerHPBar",
                                    new Vector2(0, 0.5f), new Vector2(0, 0.5f),
                                    new Vector2(130, 0), new Vector2(150, 18),
                                    COL_HP_POS);

        // Timer in center
        var timerTxt = CreateLabel(hud, "Timer", "90",
                                   new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
                                   Vector2.zero, new Vector2(70, 40), Color.white, 28, TextAlignmentOptions.Center);

        // AI HP bar (right side, fills right-to-left)
        var aiBar = CreateHPBar(hud, "AIHPBar",
                                new Vector2(1, 0.5f), new Vector2(1, 0.5f),
                                new Vector2(-130, 0), new Vector2(150, 18),
                                COL_HP_POS);
        aiBar.fillRect.GetComponent<Image>().color = COL_HP_NEG;
        aiBar.direction = Slider.Direction.RightToLeft;

        // AI label
        CreateLabel(hud, "AILabel", "RIVAL",
                    new Vector2(1, 0.5f), new Vector2(1, 0.5f),
                    new Vector2(-50, 0), new Vector2(80, 30), COL_BLUE, 14, TextAlignmentOptions.Right);

        // ── Menu panel ────────────────────────────────────────────────────────
        var menu = CreatePanel(canvasGO, "MenuPanel", new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
                               Vector2.zero, new Vector2(300, 200));
        menu.GetComponent<Image>().color = new Color(0.04f, 0.04f, 0.08f, 0.92f);

        CreateLabel(menu, "Title", "REDTAIL BATTLE",
                    new Vector2(0.5f, 1), new Vector2(0.5f, 1),
                    new Vector2(0, -30), new Vector2(280, 50), COL_ORANGE, 26, TextAlignmentOptions.Center);

        CreateLabel(menu, "Instructions",
                    "A/D or ←/→  Move\nSPACE  Punch\nX / K  Kick\nENTER  Start",
                    new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
                    new Vector2(0, 10), new Vector2(260, 90), Color.white, 13, TextAlignmentOptions.Center);

        CreateButton(menu, "StartButton", "PRESS ENTER TO START",
                     new Vector2(0.5f, 0), new Vector2(0.5f, 0),
                     new Vector2(0, 25), new Vector2(250, 36), COL_ORANGE);

        // ── Game-over panel ───────────────────────────────────────────────────
        var over = CreatePanel(canvasGO, "GameOverPanel", new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f),
                               Vector2.zero, new Vector2(300, 160));
        over.GetComponent<Image>().color = new Color(0.04f, 0.04f, 0.08f, 0.92f);
        over.SetActive(false);

        var resultTxt = CreateLabel(over, "Result", "YOU WIN!",
                                    new Vector2(0.5f, 1), new Vector2(0.5f, 1),
                                    new Vector2(0, -30), new Vector2(280, 55), COL_HP_POS, 30, TextAlignmentOptions.Center);

        CreateButton(over, "RetryButton", "RETRY",
                     new Vector2(0.5f, 0), new Vector2(0.5f, 0),
                     new Vector2(-70, 25), new Vector2(110, 34), COL_ORANGE);

        CreateButton(over, "MenuButton", "MENU",
                     new Vector2(0.5f, 0), new Vector2(0.5f, 0),
                     new Vector2(70, 25), new Vector2(110, 34), COL_DARK);

        // ── UIManager ─────────────────────────────────────────────────────────
        var uiMgrGO = new GameObject("UIManager");
        var uiMgr   = uiMgrGO.AddComponent<UIManager>();

        uiMgr.playerHPBar  = playerBar;
        uiMgr.aiHPBar      = aiBar;
        uiMgr.timerText    = timerTxt;
        uiMgr.hudPanel     = hud;
        uiMgr.menuPanel    = menu;
        uiMgr.gameOverPanel = over;
        uiMgr.resultText   = resultTxt;

        // Wire start / retry / menu buttons
        uiMgr.startButton = menu.transform.Find("StartButton")?.GetComponent<Button>();
        uiMgr.retryButton = over.transform.Find("RetryButton")?.GetComponent<Button>();
        uiMgr.menuButton  = over.transform.Find("MenuButton")?.GetComponent<Button>();
    }

    // ── UI factory helpers ─────────────────────────────────────────────────────

    static GameObject CreatePanel(GameObject parent, string name,
                                  Vector2 anchorMin, Vector2 anchorMax,
                                  Vector2 anchoredPos, Vector2 sizeDelta)
    {
        var go  = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        var img = go.AddComponent<Image>();
        img.color = Color.clear;
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin     = anchorMin;
        rt.anchorMax     = anchorMax;
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta     = sizeDelta;
        return go;
    }

    static TextMeshProUGUI CreateLabel(GameObject parent, string name, string text,
                                       Vector2 anchorMin, Vector2 anchorMax,
                                       Vector2 anchoredPos, Vector2 sizeDelta,
                                       Color color, float fontSize, TextAlignmentOptions align)
    {
        var go  = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        var tmp = go.AddComponent<TextMeshProUGUI>();
        tmp.text      = text;
        tmp.color     = color;
        tmp.fontSize  = fontSize;
        tmp.alignment = align;
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin      = anchorMin;
        rt.anchorMax      = anchorMax;
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta      = sizeDelta;
        return tmp;
    }

    static Slider CreateHPBar(GameObject parent, string name,
                               Vector2 anchorMin, Vector2 anchorMax,
                               Vector2 anchoredPos, Vector2 sizeDelta, Color fillColor)
    {
        var go  = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        var slider = go.AddComponent<Slider>();
        slider.minValue = 0; slider.maxValue = 1; slider.value = 1;
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin       = anchorMin;
        rt.anchorMax       = anchorMax;
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta       = sizeDelta;

        // Background
        var bg   = new GameObject("Background");
        bg.transform.SetParent(go.transform, false);
        var bgImg = bg.AddComponent<Image>();
        bgImg.color = new Color(0.2f, 0.2f, 0.2f, 1f);
        var bgRt = bg.GetComponent<RectTransform>();
        bgRt.anchorMin = Vector2.zero; bgRt.anchorMax = Vector2.one;
        bgRt.offsetMin = Vector2.zero; bgRt.offsetMax = Vector2.zero;

        // Fill area
        var fillArea   = new GameObject("Fill Area");
        fillArea.transform.SetParent(go.transform, false);
        var faRt = fillArea.AddComponent<RectTransform>();
        faRt.anchorMin = Vector2.zero; faRt.anchorMax = Vector2.one;
        faRt.offsetMin = Vector2.zero; faRt.offsetMax = Vector2.zero;

        var fill   = new GameObject("Fill");
        fill.transform.SetParent(fillArea.transform, false);
        var fillImg = fill.AddComponent<Image>();
        fillImg.color = fillColor;
        var fillRt = fill.GetComponent<RectTransform>();
        fillRt.anchorMin = Vector2.zero; fillRt.anchorMax = Vector2.one;
        fillRt.offsetMin = Vector2.zero; fillRt.offsetMax = Vector2.zero;

        slider.fillRect = fillRt;
        return slider;
    }

    static Button CreateButton(GameObject parent, string name, string label,
                                Vector2 anchorMin, Vector2 anchorMax,
                                Vector2 anchoredPos, Vector2 sizeDelta, Color bg)
    {
        var go  = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        var img = go.AddComponent<Image>();
        img.color = bg;
        var btn = go.AddComponent<Button>();
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin        = anchorMin;
        rt.anchorMax        = anchorMax;
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta        = sizeDelta;

        var txtGO = new GameObject("Text");
        txtGO.transform.SetParent(go.transform, false);
        var tmp = txtGO.AddComponent<TextMeshProUGUI>();
        tmp.text      = label;
        tmp.fontSize  = 12;
        tmp.alignment = TextAlignmentOptions.Center;
        tmp.color     = Color.white;
        var trt = txtGO.GetComponent<RectTransform>();
        trt.anchorMin = Vector2.zero; trt.anchorMax = Vector2.one;
        trt.offsetMin = Vector2.zero; trt.offsetMax = Vector2.zero;

        return btn;
    }
}
#endif
