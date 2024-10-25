/*
 * Copyright (C) 2018 Apple Inc. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY APPLE INC. AND ITS CONTRIBUTORS ``AS IS''
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL APPLE INC. OR ITS CONTRIBUTORS
 * BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "config.h"
#include "WebPageInspectorTargetController.h"

#include "MessageSenderInlines.h"
#include "WebPage.h"
#include "WebPageInspectorTargetFrontendChannel.h"
#include "WebPageProxyMessages.h"
#include <wtf/TZoneMallocInlines.h>

namespace WebKit {

WTF_MAKE_TZONE_ALLOCATED_IMPL(WebPageInspectorTargetController);

WebPageInspectorTargetController::WebPageInspectorTargetController(WebPage& page)
    : m_page(page)
    , m_pageTarget(page)
{
    // Do not send the page target to the UIProcess, the WebPageProxy will manager this for us.
    m_targets.set(m_pageTarget.identifier(), &m_pageTarget);
}

WebPageInspectorTargetController::~WebPageInspectorTargetController() = default;

Ref<WebPage> WebPageInspectorTargetController::protectedPage() const
{
    return m_page.get();
}

void WebPageInspectorTargetController::addTarget(Inspector::InspectorTarget& target)
{
    auto addResult = m_targets.set(target.identifier(), &target);
    ASSERT_UNUSED(addResult, addResult.isNewEntry);

    protectedPage()->send(Messages::WebPageProxy::CreateInspectorTarget(target.identifier(), target.type()));
}

void WebPageInspectorTargetController::removeTarget(Inspector::InspectorTarget& target)
{
    ASSERT_WITH_MESSAGE(target.identifier() != m_pageTarget.identifier(), "Should never remove the main target.");

    protectedPage()->send(Messages::WebPageProxy::DestroyInspectorTarget(target.identifier()));

    m_targets.remove(target.identifier());
}

void WebPageInspectorTargetController::connectInspector(const String& targetId, Inspector::FrontendChannel::ConnectionType connectionType)
{
    auto target = m_targets.get(targetId);
    if (!target)
        return;

    target->connect(connectionType);
}

void WebPageInspectorTargetController::disconnectInspector(const String& targetId)
{
    auto target = m_targets.get(targetId);
    if (!target)
        return;

    target->disconnect();
}

void WebPageInspectorTargetController::sendMessageToTargetBackend(const String& targetId, const String& message)
{
    auto target = m_targets.get(targetId);
    if (!target)
        return;

    target->sendMessageToTargetBackend(message);
}

} // namespace WebKit
