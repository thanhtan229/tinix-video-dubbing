from PySide6 import QtCore, QtGui, QtWidgets


def _make_action(ui, name):
    action = QtGui.QAction()
    action.setObjectName(name)
    setattr(ui, name, action)
    return action


def _fill_menu(menu, actions):
    for action in actions:
        menu.addAction(action)
        menu.addSeparator()


def _fill_menu_h(menu, actions):
    for action in actions:
        menu.addSeparator()
        menu.addAction(action)
    menu.addSeparator()


def _setup_actions_and_menus(ui, MainWindow):
    ui.menuBar = QtWidgets.QMenuBar()
    ui.menuBar.setObjectName("menuBar")
    ui.menu_Key = QtWidgets.QMenu(ui.menuBar)
    ui.menu_Key.setObjectName("menu_Key")
    ui.menu_TTS = QtWidgets.QMenu(ui.menuBar)
    ui.menu_TTS.setObjectName("menu_TTS")
    ui.menu_RECOGN = QtWidgets.QMenu(ui.menuBar)
    ui.menu_RECOGN.setObjectName("menu_RECOGN")
    ui.menu = QtWidgets.QMenu(ui.menuBar)
    ui.menu.setObjectName("menu")
    ui.menu_H = QtWidgets.QMenu(ui.menuBar)
    ui.menu_H.setObjectName("menu_H")
    MainWindow.setMenuBar(ui.menuBar)

    ui.toolBar = QtWidgets.QToolBar()
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    sizePolicy.setHorizontalStretch(1)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(ui.toolBar.sizePolicy().hasHeightForWidth())
    ui.toolBar.setSizePolicy(sizePolicy)
    ui.toolBar.setMinimumSize(QtCore.QSize(0, 0))
    ui.toolBar.setMaximumSize(QtCore.QSize(16777215, 16777215))
    ui.toolBar.setMovable(True)
    # ui.toolBar.setIconSize(QtCore.QSize(100, 40))
    ui.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    ui.toolBar.setFloatable(True)
    ui.toolBar.setStyleSheet("""
    QToolBar {
        background-color: #161E26;
        border-right: 1px solid #32414B;
        padding: 8px 6px;
        spacing: 6px;
    }
    QToolBar QPushButton, QToolBar QToolButton {
        min-width: 240px;
        max-width: 240px;
        min-height: 42px;
        max-height: 42px;
        padding-left: 16px;
        padding-right: 10px;
        text-align: left;
        font-weight: 600;
        font-size: 13px;
        border-radius: 8px;
        background-color: #212C36;
        color: #DFE1E2;
        border: 1px solid #384956;
    }
    QToolBar QPushButton:hover, QToolBar QToolButton:hover {
        background-color: #2A3844;
        border-color: #2F7579;
        color: #FFFFFF;
    }
    QToolBar QPushButton:checked, QToolBar QToolButton:checked {
        background-color: #124548;
        border-left: 4px solid #FF4800;
        color: #FFFFFF;
        font-weight: 700;
    }
""")
    MainWindow.addToolBar(QtCore.Qt.LeftToolBarArea, ui.toolBar)

    _make_action(ui, "actionbaidu_key")
    _make_action(ui, "actionali_key")
    _make_action(ui, "actionchatgpt_key")
    _make_action(ui, "actionzhipuai_key")
    _make_action(ui, "actionsiliconflow_key")
    _make_action(ui, "actiondeepseek_key")
    _make_action(ui, "actionminimax_key")
    _make_action(ui, "actionqwenmt_key")
    _make_action(ui, "actionopenrouter_key")
    _make_action(ui, "actionlitellm_key")
    _make_action(ui, "actionlibretranslate_key")
    _make_action(ui, "actionopenaitts_key")
    _make_action(ui, "actionxaitts_key")
    _make_action(ui, "actionxiaomi_key")
    _make_action(ui, "actionqwentts_key")
    _make_action(ui, "actionopenairecognapi_key")
    _make_action(ui, "actionparakeet_key")
    _make_action(ui, "actionai302_key")
    _make_action(ui, "actionlocalllm_key")
    _make_action(ui, "actionzijiehuoshan_key")
    _make_action(ui, "actiondeepL_key")
    _make_action(ui, "actionazure_tts")
    _make_action(ui, "action_ffmpeg")
    _make_action(ui, "action_git")
    _make_action(ui, "action_issue")
    _make_action(ui, "actiondeepLX_address")
    _make_action(ui, "actionclone_address")
    _make_action(ui, "actionkokoro_address")
    _make_action(ui, "actionchattts_address")
    _make_action(ui, "actiontts_api")
    _make_action(ui, "actionminimaxi_api")
    _make_action(ui, "actiontrans_api")
    _make_action(ui, "actionrecognapi")
    _make_action(ui, "actionsttapi")
    _make_action(ui, "actionwhisperx")
    _make_action(ui, "actiondeepgram")
    _make_action(ui, "actionxxl")
    _make_action(ui, "actionzijierecognmodel_api")
    _make_action(ui, "actiontts_gptsovits")
    _make_action(ui, "actiontts_chatterbox")
    _make_action(ui, "actiontts_cosyvoice")
    _make_action(ui, "actiontts_qwenttslocal")
    _make_action(ui, "actiontts_fishtts")
    _make_action(ui, "actiontts_gradiowin")
    _make_action(ui, "actiontts_refaudio")
    _make_action(ui, "actiontts_doubao2")
    _make_action(ui, "action_website")
    _make_action(ui, "action_blog")
    _make_action(ui, "action_discord")
    _make_action(ui, "action_gtrans")
    _make_action(ui, "action_cuda")
    _make_action(ui, "action_online")
    _make_action(ui, "actiontencent_key")
    _make_action(ui, "action_about")

    ui.action_biaozhun = QtGui.QAction()
    ui.action_biaozhun.setCheckable(True)
    ui.action_biaozhun.setChecked(True)
    ui.action_biaozhun.setObjectName("action_biaozhun")

    _make_action(ui, "action_yuyinshibie")
    _make_action(ui, "action_yuyinhecheng")

    ui.action_tiquzimu = QtGui.QAction()
    ui.action_tiquzimu.setCheckable(True)
    ui.action_tiquzimu.setObjectName("action_tiquzimu")

    _make_action(ui, "action_yingyinhebing")
    _make_action(ui, "action_clipvideo")
    _make_action(ui, "action_realtime_stt")
    _make_action(ui, "action_textmatching")
    _make_action(ui, "action_hun")
    _make_action(ui, "action_formatsrtfiles")
    _make_action(ui, "action_fanyi")
    _make_action(ui, "action_hebingsrt")
    _make_action(ui, "action_clearcache")
    _make_action(ui, "action_set_proxy")
    _make_action(ui, "actionazure_key")
    _make_action(ui, "actiongemini_key")
    _make_action(ui, "actioncamb_key")
    _make_action(ui, "actionElevenlabs_key")
    _make_action(ui, "actionwatermark")
    _make_action(ui, "actionsepar")
    _make_action(ui, "actionsetini")
    ui.actionvideoandaudio = QtGui.QAction()
    ui.actionvideoandaudio.setObjectName("videoandaudio")
    ui.actionvideoandaudio = QtGui.QAction()
    ui.actionvideoandaudio.setObjectName("videoandaudio")
    _make_action(ui, "actionvideoandsrt")
    _make_action(ui, "actionformatcover")
    _make_action(ui, "actionsubtitlescover")
    _make_action(ui, "actionsrtmultirole")
    _make_action(ui, "action_yinshipinfenli")

    _fill_menu(ui.menu_Key, [
        ui.actionbaidu_key, ui.actionali_key, ui.actiontencent_key,
        ui.actionai302_key, ui.actionchatgpt_key, ui.actionlocalllm_key,
        ui.actionzhipuai_key, ui.actionsiliconflow_key, ui.actiondeepseek_key,
        ui.actionxiaomi_key, ui.actionminimax_key, ui.actionqwenmt_key,
        ui.actionopenrouter_key, ui.actionlitellm_key, ui.actionlibretranslate_key,
        ui.actionzijiehuoshan_key, ui.actionazure_key, ui.actiongemini_key,
        ui.actioncamb_key, ui.actiondeepL_key, ui.actiondeepLX_address,
        ui.actiontrans_api,
    ])

    _fill_menu(ui.menu_TTS, [
        ui.actiontts_refaudio, ui.actionclone_address, ui.actionkokoro_address,
        ui.actionchattts_address, ui.actiontts_gptsovits, 
        ui.actiontts_cosyvoice, ui.actiontts_qwenttslocal, ui.actionqwentts_key,
        ui.actiontts_fishtts, ui.actiontts_gradiowin, ui.actionai302_key,
        ui.actiontts_doubao2, ui.actionElevenlabs_key, ui.actionazure_tts,
        ui.actionxaitts_key, ui.actionopenaitts_key, ui.actionminimaxi_api,
        ui.actiontts_api, ui.actiontts_chatterbox,
    ])

    _fill_menu(ui.menu_RECOGN, [
        ui.actionzijierecognmodel_api, ui.actionopenairecognapi_key,
        ui.actionparakeet_key, ui.actionrecognapi, ui.actionai302_key,
        ui.actionsttapi, ui.actionwhisperx, ui.actiondeepgram,
        ui.actionxxl,
    ])

    _fill_menu(ui.menu, [
        ui.actionsetini, ui.action_clipvideo, ui.actionwatermark,
        ui.action_realtime_stt, ui.action_textmatching, ui.action_yingyinhebing,
        ui.actionvideoandaudio, ui.actionvideoandsrt, ui.actionformatcover,
        ui.actionsubtitlescover, ui.actionsrtmultirole, ui.action_yinshipinfenli,
        ui.action_hun,ui.action_formatsrtfiles, ui.action_hebingsrt, ui.actionsepar, ui.action_set_proxy,
    ])
    ui.menu.addAction(ui.action_clearcache)
    ui.menu.addSeparator()

    _fill_menu_h(ui.menu_H, [
        ui.action_website, ui.action_blog, ui.action_discord,
        ui.action_gtrans, ui.action_cuda, ui.action_git, ui.action_issue,
        ui.action_ffmpeg, ui.action_online, ui.action_about,
    ])

    ui.menuBar.addAction(ui.menu_Key.menuAction())
    ui.menuBar.addAction(ui.menu_TTS.menuAction())
    ui.menuBar.addAction(ui.menu_RECOGN.menuAction())
    ui.menuBar.addAction(ui.menu.menuAction())
    ui.menuBar.addAction(ui.menu_H.menuAction())

    tab_defs = [
        (ui.action_biaozhun, "btn_tab_0"),
        (ui.action_tiquzimu, "btn_tab_1"),
        (ui.action_yuyinshibie, "btn_tab_2"),
        (ui.action_yuyinhecheng, "btn_tab_3"),
        (ui.action_fanyi, "btn_tab_4"),
        (ui.actionsrtmultirole, "btn_tab_5"),
        (ui.action_yingyinhebing, "btn_tab_6")
    ]
    ui.tab_button_group = QtWidgets.QButtonGroup(MainWindow)
    ui.tab_button_group.setExclusive(True)
    ui.tab_buttons = []
    for idx, (act, btn_name) in enumerate(tab_defs):
        act.setCheckable(True)
        btn = QtWidgets.QPushButton()
        btn.setObjectName(btn_name)
        btn.setCheckable(True)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setText(act.text())
        btn.setToolTip(act.toolTip())
        btn.clicked.connect(act.trigger)
        act.changed.connect(lambda b=btn, a=act: b.setText(a.text()))
        setattr(ui, btn_name, btn)
        ui.tab_buttons.append(btn)
        ui.tab_button_group.addButton(btn, idx)
        ui.toolBar.addWidget(btn)
    ui.btn_tab_0.setChecked(True)
    ui.action_biaozhun.setChecked(True)
