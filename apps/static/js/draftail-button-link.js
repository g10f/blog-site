// Draftail plugin for the BUTTON_LINK entity registered in register_button_link_feature (base/wagtail_hooks.py).
// Wagtail only ships editor plugins (source + decorator) for its own entity types, so a custom entity type
// needs them registered here, otherwise its toolbar button does nothing and existing buttons aren't shown.
(() => {
  const {React, DraftJS} = window;
  const {registerPlugin, LinkModalWorkflowSource, TooltipEntity} = window.draftail;
  const TYPE = 'BUTTON_LINK';

  // LinkModalWorkflowSource looks up the entity mutability by type and only knows LINK, so it creates
  // BUTTON_LINK entities without one. Re-create the new entity as MUTABLE (like LINK and like the server
  // side does), otherwise typing inside a freshly inserted button splits it.
  const withMutableEntity = (editorState) => {
    let content = editorState.getCurrentContent();
    const key = content.getLastCreatedEntityKey();
    const entity = key ? content.getEntity(key) : null;
    if (!entity || entity.getType() !== TYPE || entity.getMutability() === 'MUTABLE') {
      return editorState;
    }
    content = content.createEntity(TYPE, 'MUTABLE', entity.getData());
    const mutableKey = content.getLastCreatedEntityKey();
    editorState.getCurrentContent().getBlockMap().forEach((block) => {
      block.findEntityRanges(
        (character) => character.getEntity() === key,
        (start, end) => {
          const range = DraftJS.SelectionState.createEmpty(block.getKey()).merge({anchorOffset: start, focusOffset: end});
          content = DraftJS.Modifier.applyEntity(content, range, mutableKey);
        },
      );
    });
    return DraftJS.EditorState.set(editorState, {currentContent: content});
  };

  const ButtonLinkSource = (props) => React.createElement(LinkModalWorkflowSource, {
    ...props,
    onComplete: (editorState) => props.onComplete(withMutableEntity(editorState)),
  });

  const ButtonLink = (props) => {
    const {entityKey, contentState} = props;
    const {url} = contentState.getEntity(entityKey).getData();
    return React.createElement(TooltipEntity, {...props, icon: '#icon-hand-index', label: url || '', url});
  };

  registerPlugin({type: TYPE, source: ButtonLinkSource, decorator: ButtonLink}, 'entityTypes');
})();
